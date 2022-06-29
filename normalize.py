#!/usr/bin/env python
# coding: utf-8

import rdflib
from rdflib.namespace import SKOS, RDFS
from otsrdflib import OrderedTurtleSerializer

skosxl = rdflib.Namespace('http://www.w3.org/2008/05/skos-xl#')
skos_thes = rdflib.Namespace('http://purl.org/iso25964/skos-thes#')


def normalize(infile, outfile, do_prepare_skosmos=False):
    """
    Read and write a graph through rdflib in order to clean it up.

    """
    g = rdflib.Graph()
    g.parse(infile, format='turtle')

    if do_prepare_skosmos:
        g = prepare_skosmos(g)

    serializer = OrderedTurtleSerializer(g)
    serializer.class_order = [
        SKOS.ConceptScheme,
        SKOS.Concept,
    ]
    serializer.serialize(outfile)


def prepare_skosmos(g):
    """
    Prepare RDF for SKOSMOS

    SKOSMOS has a simple, plain-SKOS [data model]
    (https://github.com/NatLibFi/Skosmos/wiki/Data-Model). Our data model
    derives from this in two major ways that break SKOSMOS’ expectations:

    1. We use SKOS-XL as the lexicalization scheme, and
    2. we use the more specific sub-properties of `skos:broader` defined by
    skos-thes.

    We map these to plain SKOS before loading the dataset into SKOSMOS.
    """

    # ## Broaders/Narrowers

    # We use `skos-thes:broaderGeneric` and `skos-thes:broaderPartitive`.
    # SKOSMOS does not use these for building the hierarchy tree, so we have
    # to make them known as subtypes of `skos:broader`, _and_ we need to add
    # plain `skos:broader` relations. We also need to explicitly add the
    # implicit inverse (narrower) properties.

    # Add sub-properties for skos-thes.

    g.add((skos_thes.broaderPartitive, RDFS.subPropertyOf, SKOS.broader))
    g.add((skos_thes.broaderGeneric, RDFS.subPropertyOf, SKOS.broader))
    g.add((skos_thes.narrowerPartitive, RDFS.subPropertyOf, SKOS.narrower))
    g.add((skos_thes.narrowerGeneric, RDFS.subPropertyOf, SKOS.narrower))

    # Add inverse relations.

    g.update("""
    INSERT {
        ?part skos:broader ?parent .
        ?parent skos-thes:narrowerPartitive ?part .
        ?parent skos:narrower ?part .
    }
    WHERE {
        ?part skos-thes:broaderPartitive ?parent .
    }
    """)

    g.update("""
    INSERT {
        ?part skos:broader ?parent .
        ?parent skos-thes:narrowerGeneric ?part .
        ?parent skos:narrower ?part .
    }
    WHERE {
        ?part skos-thes:broaderGeneric ?parent .
    }
    """)

    # ## Lexicalization

    # We add plain skos labels based on the SKOS-XL properties.

    g.update(
        """INSERT { ?concept skos:prefLabel ?label . }
           WHERE {
               ?concept skosxl:prefLabel ?xlabel .
               ?xlabel skosxl:literalForm ?label .
           }""")

    g.update(
        """INSERT { ?concept skos:altLabel ?label . }
           WHERE {
               ?concept skosxl:altLabel ?xlabel .
               ?xlabel skosxl:literalForm ?label .
           }""")

    # ## Editorial notes

    # We remove the editorial notes that are not meant for public display.

    g.update(
        """DELETE { ?concept skos:editorialNote ?note }
        WHERE {
            ?concept skos:editorialNote ?note .
            FILTER ( STRSTARTS ( ?note, "Figure label" ) )
        }""")

    # ## Illustrations

    # For the time being, we have both direct image links as well as stable
    # URIs for images in VocBench, because it displays only the latter as
    # images. We remove these redundant links here.

    g.update("""
        DELETE { ?concept foaf:depiction ?old_img . }
        WHERE {
            ?concept a skos:Concept .
            ?concept foaf:depiction ?old_img .
            FILTER( STRSTARTS( STR(?old_img), "https://pages.ceres.rub.de" ) )
        }
    """)

    return g


def main():
    import argparse
    parser = argparse.ArgumentParser()
    # General arguments
    parser.add_argument('infile', type=argparse.FileType('rb'))
    parser.add_argument('--outfile', '-o', type=argparse.FileType('wb'))
    parser.add_argument('--skosmos', '-s', action='store_true')
    args = parser.parse_args()

    normalize(args.infile, args.outfile, do_prepare_skosmos=args.skosmos)


if __name__ == '__main__':
    main()
