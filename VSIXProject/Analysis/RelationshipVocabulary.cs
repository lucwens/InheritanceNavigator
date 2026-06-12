using System;
using System.Collections.Generic;
using System.Text;

namespace VSIXProject.Analysis
{
    /// <summary>How an edge relates two nodes, after normalising Graphify's relationship label.</summary>
    public enum RelationshipKind
    {
        Unknown = 0,

        /// <summary>An owner contains a member (class &#8594; method).</summary>
        Containment,

        /// <summary>Edge points from the derived class to its base class.</summary>
        InheritsDerivedToBase,

        /// <summary>Edge points from the base class to the derived class.</summary>
        InheritsBaseToDerived,

        /// <summary>Edge points from the overriding method to the overridden one.</summary>
        OverrideChildToParent,

        /// <summary>Edge points from the overridden method to the overriding one.</summary>
        OverrideParentToChild,
    }

    /// <summary>
    /// Maps the free-form node "type" and edge "relationship" strings emitted by Graphify onto the
    /// concepts the Inheritance Navigator understands. Matching is intentionally fuzzy (case- and
    /// punctuation-insensitive, substring based) because the exact vocabulary varies between Graphify
    /// versions and languages. This is the one place to adjust if a particular database uses different
    /// labels.
    /// </summary>
    public static class RelationshipVocabulary
    {
        private static readonly string[] ClassTokens =
        {
            "class", "struct", "interface", "trait", "record", "typedef", "type",
        };

        private static readonly string[] MethodTokens =
        {
            "method", "function", "func", "member", "ctor", "constructor", "destructor", "operator",
        };

        // Normalised (letters only, lowercase) relationship tokens.
        private static readonly HashSet<string> ContainmentTokens = MakeSet(
            "contains", "contain", "defines", "define", "declares", "declare",
            "hasmethod", "hasmember", "hasfunction", "member", "method", "memberof",
            "owns", "has", "child", "encloses");

        private static readonly HashSet<string> DerivedToBaseTokens = MakeSet(
            "extends", "extend", "inherits", "inherit", "inheritsfrom", "inheritfrom",
            "subclassof", "subtypeof", "derivesfrom", "derivefrom", "derives", "derive",
            "isa", "specializes", "basetype", "base", "inheritance", "inheritsfromclass");

        private static readonly HashSet<string> BaseToDerivedTokens = MakeSet(
            "baseof", "superclassof", "parentof", "inheritedby", "derivedby", "extendedby",
            "subclassedby", "specializedby");

        private static readonly HashSet<string> ChildToParentOverrideTokens = MakeSet(
            "overrides", "override", "overridesmethod", "implements", "implement",
            "implementsmethod", "redefines", "redefine");

        private static readonly HashSet<string> ParentToChildOverrideTokens = MakeSet(
            "overriddenby", "implementedby", "redefinedby");

        public static bool IsClassType(string type)
        {
            return ContainsAnyToken(type, ClassTokens) && !ContainsAnyToken(type, MethodTokens);
        }

        public static bool IsMethodType(string type)
        {
            return ContainsAnyToken(type, MethodTokens);
        }

        public static RelationshipKind Classify(string relationship)
        {
            string token = Normalize(relationship);
            if (token.Length == 0)
            {
                return RelationshipKind.Unknown;
            }

            if (ContainmentTokens.Contains(token))
            {
                return RelationshipKind.Containment;
            }

            if (ChildToParentOverrideTokens.Contains(token))
            {
                return RelationshipKind.OverrideChildToParent;
            }

            if (ParentToChildOverrideTokens.Contains(token))
            {
                return RelationshipKind.OverrideParentToChild;
            }

            if (BaseToDerivedTokens.Contains(token))
            {
                return RelationshipKind.InheritsBaseToDerived;
            }

            if (DerivedToBaseTokens.Contains(token))
            {
                return RelationshipKind.InheritsDerivedToBase;
            }

            // Substring fallbacks for compound labels such as "CLASS_INHERITS_FROM".
            if (ContainsToken(token, "overriddenby") || ContainsToken(token, "implementedby"))
            {
                return RelationshipKind.OverrideParentToChild;
            }

            if (ContainsToken(token, "override") || ContainsToken(token, "implements"))
            {
                return RelationshipKind.OverrideChildToParent;
            }

            if (ContainsToken(token, "baseof") || ContainsToken(token, "parentof") || ContainsToken(token, "inheritedby"))
            {
                return RelationshipKind.InheritsBaseToDerived;
            }

            if (ContainsToken(token, "inherit") || ContainsToken(token, "extends") || ContainsToken(token, "subclass"))
            {
                return RelationshipKind.InheritsDerivedToBase;
            }

            if (ContainsToken(token, "contains") || ContainsToken(token, "defines") || ContainsToken(token, "declares"))
            {
                return RelationshipKind.Containment;
            }

            return RelationshipKind.Unknown;
        }

        private static bool ContainsAnyToken(string type, string[] tokens)
        {
            if (string.IsNullOrEmpty(type))
            {
                return false;
            }

            string normalized = Normalize(type);
            foreach (string token in tokens)
            {
                if (normalized.IndexOf(token, StringComparison.Ordinal) >= 0)
                {
                    return true;
                }
            }

            return false;
        }

        private static bool ContainsToken(string normalized, string token)
        {
            return normalized.IndexOf(token, StringComparison.Ordinal) >= 0;
        }

        private static string Normalize(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                return string.Empty;
            }

            var sb = new StringBuilder(value.Length);
            foreach (char c in value)
            {
                if (char.IsLetter(c))
                {
                    sb.Append(char.ToLowerInvariant(c));
                }
            }

            return sb.ToString();
        }

        private static HashSet<string> MakeSet(params string[] values)
        {
            return new HashSet<string>(values, StringComparer.Ordinal);
        }
    }
}
