// Program.cs
// .NET 7 Console app
// dotnet add package MongoDB.Driver

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;
using MongoDB.Driver;
using System.Globalization;

namespace MigracaoMongo
{
    [BsonIgnoreExtraElements]
    public class Canal
    {
        [BsonId]
        public ObjectId Id { get; set; }
        public string Grupo { get; set; }
        public string grupoID { get; set; }

        // campos opcionais (mantidos apenas por clareza)
        public string IdVideo { get; set; }
        public string Nome { get; set; }
        public string Url { get; set; }
        public string Logo { get; set; }
    }

    [BsonIgnoreExtraElements]
    public class GrupoDoc
    {
        [BsonId]
        public ObjectId Id { get; set; }
        public string grupoID { get; set; }
        public string nome { get; set; }
        public string nome_norm { get; set; }
        public int count { get; set; }
    }

    internal static class Program2
    {
        // ===== CONFIG =====
        private const string MONGO_URI = "mongodb+srv://teste:teste@cluster0.zjhbafz.mongodb.net/M3U?retryWrites=true&w=majority";
        private const string DB_NAME = "M3U";
        private const string COL_CANAIS = "canais";
        private const string COL_GRUPOS = "grupos";
        private const int BATCH_SIZE = 1000;
        // ==================

        private static readonly Regex WhitespaceRe = new(@"\s+", RegexOptions.Compiled);
        private static readonly Regex EdgeCleanRe = new(@"[^a-z0-9\s-]", RegexOptions.Compiled | RegexOptions.IgnoreCase);

        static async Task<int> Main2(string[] args)
        {
            var client = new MongoClient(MONGO_URI);
            var db = client.GetDatabase(DB_NAME);
            var canais = db.GetCollection<Canal>(COL_CANAIS);
            var grupos = db.GetCollection<GrupoDoc>(COL_GRUPOS);

            try
            {
                // --- 1) Agregação: obter valores distintos de Grupo com contagem ---
                var match = new BsonDocument
                {
                    { "$match", new BsonDocument("Grupo", new BsonDocument("$nin", new BsonArray { BsonNull.Value, "" })) }
                };
                var group = new BsonDocument
                {
                    {
                        "$group",
                        new BsonDocument
                        {
                            { "_id", "$Grupo" },
                            { "count", new BsonDocument("$sum", 1) }
                        }
                    }
                };

                var pipeline = new[] { match, group };
                var aggCursor = await canais.AggregateAsync<BsonDocument>(pipeline);
                var groupList = await aggCursor.ToListAsync();

                if (groupList == null || groupList.Count == 0)
                {
                    Console.WriteLine("Nenhum valor de Grupo encontrado para processar.");
                    return 0;
                }

                // --- 2) Construir mapa normalizado -> (original -> count) ---
                var mapNorm = new Dictionary<string, Dictionary<string, int>>(StringComparer.Ordinal);
                foreach (var doc in groupList)
                {
                    var orig = doc.GetValue("_id").AsString;
                    var cntBson = doc.GetValue("count");
                    var cnt = cntBson.IsInt32 ? cntBson.AsInt32 : (cntBson.IsInt64 ? (int)cntBson.AsInt64 : Convert.ToInt32(cntBson.ToInt64()));
                    var norm = NormalizeForId(orig);
                    if (!mapNorm.TryGetValue(norm, out var inner))
                    {
                        inner = new Dictionary<string, int>(StringComparer.Ordinal);
                        mapNorm[norm] = inner;
                    }
                    if (inner.ContainsKey(orig)) inner[orig] += cnt;
                    else inner[orig] = cnt;
                }

                // --- 3) Upsert na coleção grupos (bulk por batches) ---
                var upsertModels = new List<WriteModel<GrupoDoc>>();
                foreach (var kv in mapNorm)
                {
                    var norm = kv.Key;
                    var variants = kv.Value;
                    var nomeRepr = ChooseRepresentative(variants);
                    var doc = new GrupoDoc
                    {
                        grupoID = norm,
                        nome = nomeRepr,
                        nome_norm = norm,
                        count = variants.Values.Sum()
                    };

                    var filterUpsert = Builders<GrupoDoc>.Filter.Eq(g => g.grupoID, norm);
                    var update = Builders<GrupoDoc>.Update
                        .Set(g => g.nome, doc.nome)
                        .Set(g => g.nome_norm, doc.nome_norm)
                        .Set(g => g.count, doc.count)
                        .SetOnInsert(g => g.grupoID, doc.grupoID);

                    var upsert = new UpdateOneModel<GrupoDoc>(filterUpsert, update) { IsUpsert = true };
                    upsertModels.Add(upsert);
                }

                for (int i = 0; i < upsertModels.Count; i += BATCH_SIZE)
                {
                    var batch = upsertModels.Skip(i).Take(BATCH_SIZE).ToList();
                    if (batch.Count > 0)
                    {
                        var res = await grupos.BulkWriteAsync(batch);
                        Console.WriteLine($"Upsert grupos batch {i / BATCH_SIZE + 1}: matched={res.MatchedCount}, upserted={res.Upserts?.Count ?? 0}, modified={res.ModifiedCount}");
                    }
                }

                // --- 4) Atualizar documentos 'canais' adicionando campo grupoID ---
                var updateOps = new List<WriteModel<BsonDocument>>();
                long totalUpdated = 0;

                // Project only _id and Grupo to avoid deserialization issues and reduce payload
                var projection = Builders<BsonDocument>.Projection.Include("_id").Include("Grupo");
                using (var cursorCanais = await canais.Database.GetCollection<BsonDocument>(COL_CANAIS)
                                                           .Find(FilterDefinition<BsonDocument>.Empty)
                                                           .Project(projection)
                                                           .ToCursorAsync())
                {
                    while (await cursorCanais.MoveNextAsync())
                    {
                        foreach (var doc in cursorCanais.Current)
                        {
                            var id = doc.GetValue("_id").AsObjectId;
                            var orig = doc.Contains("Grupo") ? doc.GetValue("Grupo").AsString : "";
                            var norm = NormalizeForId(orig);
                            if (string.IsNullOrEmpty(norm)) norm = "sem-grupo";

                            var filterUpdate = Builders<BsonDocument>.Filter.Eq("_id", id);
                            var update = Builders<BsonDocument>.Update.Set("grupoID", norm);
                            updateOps.Add(new UpdateOneModel<BsonDocument>(filterUpdate, update));

                            if (updateOps.Count >= BATCH_SIZE)
                            {
                                var res = await canais.Database.GetCollection<BsonDocument>(COL_CANAIS).BulkWriteAsync(updateOps);
                                totalUpdated += res.ModifiedCount;
                                updateOps.Clear();
                            }
                        }
                    }
                }

                if (updateOps.Count > 0)
                {
                    var res = await canais.Database.GetCollection<BsonDocument>(COL_CANAIS).BulkWriteAsync(updateOps);
                    totalUpdated += res.ModifiedCount;
                    updateOps.Clear();
                }

                Console.WriteLine($"Total documentos 'canais' atualizados com grupoID: {totalUpdated}");

                // --- 5) Criar índices ---
                try
                {
                    var idxGrupos = new CreateIndexModel<GrupoDoc>(
                        Builders<GrupoDoc>.IndexKeys.Ascending(g => g.grupoID),
                        new CreateIndexOptions { Unique = true });
                    await grupos.Indexes.CreateOneAsync(idxGrupos);

                    var idxCanais = new CreateIndexModel<BsonDocument>(
                        Builders<BsonDocument>.IndexKeys.Ascending("grupoID"));
                    await canais.Database.GetCollection<BsonDocument>(COL_CANAIS).Indexes.CreateOneAsync(idxCanais);

                    Console.WriteLine("Índices criados: grupos.grupoID (unique), canais.grupoID");
                }
                catch (Exception ixEx)
                {
                    Console.WriteLine("Erro ao criar índices: " + ixEx.Message);
                }

                Console.WriteLine("Migração concluída com sucesso.");
                return 0;
            }
            catch (Exception ex)
            {
                Console.WriteLine("Erro durante migração: " + ex);
                return 2;
            }
        }

        // Gera slug-like grupoID
        private static string NormalizeForId(string s)
        {
            if (string.IsNullOrEmpty(s)) return "sem-grupo";

            var normalized = s.Normalize(NormalizationForm.FormKD);
            var sb = new StringBuilder();
            foreach (var ch in normalized)
            {
                var cat = CharUnicodeInfo.GetUnicodeCategory(ch);
                if (cat == UnicodeCategory.NonSpacingMark) continue;
                sb.Append(ch);
            }
            var noDiacritics = sb.ToString();

            noDiacritics = noDiacritics.ToLowerInvariant();
            noDiacritics = noDiacritics.Replace("–", "-").Replace("—", "-").Replace("―", "-");
            noDiacritics = EdgeCleanRe.Replace(noDiacritics, "");
            noDiacritics = WhitespaceRe.Replace(noDiacritics, " ").Trim();
            noDiacritics = noDiacritics.Replace(" ", "-");
            noDiacritics = Regex.Replace(noDiacritics, "-{2,}", "-").Trim('-');

            return string.IsNullOrEmpty(noDiacritics) ? "sem-grupo" : noDiacritics;
        }

        private static string ChooseRepresentative(Dictionary<string, int> variants)
        {
            if (variants == null || variants.Count == 0) return "";
            return variants
                .OrderByDescending(kv => kv.Value)
                .ThenBy(kv => kv.Key, StringComparer.Ordinal)
                .First().Key;
        }
    }
}
