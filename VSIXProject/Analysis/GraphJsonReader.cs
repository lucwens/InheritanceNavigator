using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Web.Script.Serialization;

namespace VSIXProject.Analysis
{
    /// <summary>A single node parsed from a Graphify <c>graph.json</c> file.</summary>
    public sealed class GraphNode
    {
        public string Id { get; set; }
        public string Label { get; set; }
        public string Type { get; set; }
        public string SourceFile { get; set; }
        public int Line { get; set; }
        public string Community { get; set; }
        public IDictionary<string, object> Raw { get; set; }
    }

    /// <summary>A single edge parsed from a Graphify <c>graph.json</c> file.</summary>
    public sealed class GraphEdge
    {
        public string Source { get; set; }
        public string Target { get; set; }
        public string Type { get; set; }
        public IDictionary<string, object> Raw { get; set; }
    }

    /// <summary>In-memory representation of a parsed graph.</summary>
    public sealed class GraphData
    {
        public GraphData()
        {
            Nodes = new List<GraphNode>();
            Edges = new List<GraphEdge>();
        }

        public bool Directed { get; set; }
        public List<GraphNode> Nodes { get; }
        public List<GraphEdge> Edges { get; }
    }

    /// <summary>
    /// Tolerant reader for Graphify's <c>graph.json</c>. Graphify serialises a NetworkX graph with
    /// <c>networkx.node_link_data</c>, producing a top-level object with <c>nodes</c> and
    /// <c>links</c> (a.k.a. <c>edges</c>) arrays. Field names vary between Graphify versions, so this
    /// reader looks up a number of candidate keys for every value rather than binding to a fixed schema.
    /// </summary>
    public static class GraphJsonReader
    {
        private static readonly string[] IdKeys = { "id", "node_id", "key", "name" };
        private static readonly string[] LabelKeys = { "label", "name", "title", "norm_label", "display", "id" };
        private static readonly string[] TypeKeys = { "type", "kind", "category", "node_type", "label_type", "entity_type" };
        private static readonly string[] FileKeys = { "source_file", "file", "file_path", "path", "filename", "filepath" };
        private static readonly string[] LineKeys = { "line", "lineno", "start_line", "line_number", "start", "row" };
        private static readonly string[] CommunityKeys = { "community", "cluster", "module" };
        private static readonly string[] EdgeSourceKeys = { "source", "src", "from", "start" };
        private static readonly string[] EdgeTargetKeys = { "target", "dst", "to", "end" };
        private static readonly string[] EdgeTypeKeys = { "type", "relation", "relationship", "rel", "label", "kind" };

        /// <summary>Reads and parses the given file. Returns <c>null</c> if it cannot be read/parsed.</summary>
        public static GraphData ReadFile(string path)
        {
            try
            {
                if (string.IsNullOrEmpty(path) || !File.Exists(path))
                {
                    return null;
                }

                string text = File.ReadAllText(path);
                return Parse(text);
            }
            catch
            {
                return null;
            }
        }

        /// <summary>Parses graph.json text. Returns <c>null</c> on failure.</summary>
        public static GraphData Parse(string json)
        {
            if (string.IsNullOrEmpty(json))
            {
                return null;
            }

            try
            {
                var serializer = new JavaScriptSerializer();
                serializer.MaxJsonLength = int.MaxValue;
                serializer.RecursionLimit = 1000;

                var root = serializer.DeserializeObject(json) as IDictionary<string, object>;
                if (root == null)
                {
                    return null;
                }

                var data = new GraphData();
                data.Directed = ToBool(GetValue(root, new[] { "directed" }), true);

                object nodesObj = GetValue(root, new[] { "nodes", "vertices" });
                foreach (var item in AsEnumerable(nodesObj))
                {
                    var dict = item as IDictionary<string, object>;
                    if (dict == null)
                    {
                        continue;
                    }

                    var node = new GraphNode();
                    node.Id = ToStr(GetValue(dict, IdKeys));
                    node.Label = ToStr(GetValue(dict, LabelKeys));
                    node.Type = ToStr(GetValue(dict, TypeKeys));
                    node.SourceFile = ToStr(GetValue(dict, FileKeys));
                    node.Line = ToInt(GetValue(dict, LineKeys));
                    node.Community = ToStr(GetValue(dict, CommunityKeys));
                    node.Raw = dict;

                    if (node.Id != null)
                    {
                        data.Nodes.Add(node);
                    }
                }

                // NetworkX node-link uses "links"; some exports keep "edges".
                object edgesObj = GetValue(root, new[] { "links", "edges" });
                foreach (var item in AsEnumerable(edgesObj))
                {
                    var dict = item as IDictionary<string, object>;
                    if (dict == null)
                    {
                        continue;
                    }

                    var edge = new GraphEdge();
                    edge.Source = ToStr(GetValue(dict, EdgeSourceKeys));
                    edge.Target = ToStr(GetValue(dict, EdgeTargetKeys));
                    edge.Type = ToStr(GetValue(dict, EdgeTypeKeys));
                    edge.Raw = dict;

                    if (edge.Source != null && edge.Target != null)
                    {
                        data.Edges.Add(edge);
                    }
                }

                return data;
            }
            catch
            {
                return null;
            }
        }

        private static object GetValue(IDictionary<string, object> dict, string[] keys)
        {
            if (dict == null)
            {
                return null;
            }

            // Exact match first (fast path), then case-insensitive fallback.
            foreach (string key in keys)
            {
                object value;
                if (dict.TryGetValue(key, out value) && value != null)
                {
                    return value;
                }
            }

            foreach (var pair in dict)
            {
                foreach (string key in keys)
                {
                    if (string.Equals(pair.Key, key, StringComparison.OrdinalIgnoreCase) && pair.Value != null)
                    {
                        return pair.Value;
                    }
                }
            }

            return null;
        }

        private static IEnumerable<object> AsEnumerable(object value)
        {
            var array = value as IEnumerable<object>;
            if (array != null)
            {
                return array;
            }

            var objArray = value as object[];
            if (objArray != null)
            {
                return objArray;
            }

            return new object[0];
        }

        private static string ToStr(object value)
        {
            if (value == null)
            {
                return null;
            }

            string s = value as string;
            if (s != null)
            {
                return s;
            }

            return Convert.ToString(value, CultureInfo.InvariantCulture);
        }

        private static int ToInt(object value)
        {
            if (value == null)
            {
                return 0;
            }

            try
            {
                if (value is int)
                {
                    return (int)value;
                }

                int result;
                if (int.TryParse(ToStr(value), NumberStyles.Integer, CultureInfo.InvariantCulture, out result))
                {
                    return result;
                }

                double d;
                if (double.TryParse(ToStr(value), NumberStyles.Float, CultureInfo.InvariantCulture, out d))
                {
                    return (int)d;
                }
            }
            catch
            {
                // fall through
            }

            return 0;
        }

        private static bool ToBool(object value, bool fallback)
        {
            if (value is bool)
            {
                return (bool)value;
            }

            bool result;
            if (value != null && bool.TryParse(ToStr(value), out result))
            {
                return result;
            }

            return fallback;
        }
    }
}
