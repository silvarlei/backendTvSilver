using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using MongoDB.Driver;

public class M3UItem
{
    public string IdVideo { get; set; }    // Chave única
    public string Grupo { get; set; } // group-title
    public string Nome { get; set; }  // Nome do canal
    public string Url { get; set; }   // URL do stream
    public string Logo { get; set; }  // tvg-logo
}

public class Program
{
    // Async Main para usar await diretamente
    public static async Task Main(string[] args)
    {
        var parser = new M3UParser();
        try
        {
            var items = await parser.ParseFromUrlAsync("https://raw.githubusercontent.com/Ramys/Iptv-Brasil-2025/refs/heads/master/Lista%20Online%2003.m3u8");
            const string outputPath = "tv.json";
            await parser.SaveAsJsonAsync(items, outputPath);
            Console.WriteLine($"Arquivo JSON gerado em: {outputPath}");

            // Insere no MongoDB depois de gerar o JSON
            await GravarNoMongoAsync(outputPath);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Erro: {ex.Message}");
        }
    }

    private static async Task GravarNoMongoAsync(string jsonFilePath)
    {
        try
        {
            if (!File.Exists(jsonFilePath))
            {
                Console.WriteLine("Arquivo JSON não encontrado.");
                return;
            }

            // Conexão com MongoDB Atlas (ajuste a connection string conforme necessário)
            var client = new MongoClient("mongodb+srv://teste:teste@cluster0.zjhbafz.mongodb.net/M3U?retryWrites=true&w=majority");
            var database = client.GetDatabase("M3U");
            var collection = database.GetCollection<M3UItem>("tv");

            // Leitura do arquivo JSON
            string json = await File.ReadAllTextAsync(jsonFilePath);
            var canais = JsonSerializer.Deserialize<List<M3UItem>>(json);

            if (canais != null && canais.Count > 0)
            {
                await collection.InsertManyAsync(canais);
                Console.WriteLine("Canais inseridos no MongoDB com sucesso!");
            }
            else
            {
                Console.WriteLine("Nenhum canal encontrado no arquivo JSON.");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Erro ao inserir no MongoDB: {ex.Message}");
        }
    }
}

public class M3UParser
{
    private static readonly Regex InfoRegex = new Regex(
        @"#EXTINF:-1(?:\s+[^=]+=""[^""]*"")*\s+tvg-logo=""(?<logo>[^""]*)""\s+group-title=""(?<group>[^""]*)""\s*,(?<name>.+)",
        RegexOptions.Compiled | RegexOptions.IgnoreCase);

    public async Task<List<M3UItem>> ParseFromUrlAsync(string m3uUrl)
    {
        using var httpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };
        var content = await httpClient.GetStringAsync(m3uUrl);

        var lines = content.Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);
        var items = new List<M3UItem>();

        for (int i = 0; i < lines.Length - 1; i++)
        {
            var line = lines[i].Trim();
            if (!line.StartsWith("#EXTINF", StringComparison.OrdinalIgnoreCase))
                continue;

            var match = InfoRegex.Match(line);
            string nome = null;
            string grupo = null;
            string logo = null;

            if (match.Success)
            {
                nome = match.Groups["name"].Value.Trim();
                grupo = match.Groups["group"].Value.Trim();
                logo = match.Groups["logo"].Value.Trim();
            }
            else
            {
                // fallback: tentar extrair nome após a vírgula, e atributos opcionais
                var idx = line.IndexOf(',');
                if (idx >= 0 && idx < line.Length - 1)
                    nome = line.Substring(idx + 1).Trim();

                var groupMatch = Regex.Match(line, @"group-title=""(?<g>[^""]*)""", RegexOptions.IgnoreCase);
                if (groupMatch.Success) grupo = groupMatch.Groups["g"].Value.Trim();

                var logoMatch = Regex.Match(line, @"tvg-logo=""(?<l>[^""]*)""", RegexOptions.IgnoreCase);
                if (logoMatch.Success) logo = logoMatch.Groups["l"].Value.Trim();
            }

            var nextLine = lines[i + 1].Trim();
            if (string.IsNullOrWhiteSpace(nextLine) || nextLine.StartsWith("#"))
                continue;

            // Somente adiciona se tiver os campos mínimos (nome e url). Grupo e logo podem ser vazios, mas você pode ajustar para torná-los obrigatórios.
            var item = new M3UItem
            {
                IdVideo = Guid.NewGuid().ToString(),
                Nome = nome ?? string.Empty,
                Grupo = grupo ?? string.Empty,
                Logo = logo ?? string.Empty,
                Url = nextLine
            };

            items.Add(item);
        }

        return items;
    }

    public async Task SaveAsJsonAsync(List<M3UItem> items, string outputPath)
    {
        var options = new JsonSerializerOptions { WriteIndented = true };
        var json = JsonSerializer.Serialize(items, options);
        await File.WriteAllTextAsync(outputPath, json);
    }
}
