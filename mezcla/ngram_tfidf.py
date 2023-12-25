#! /usr/bin/env python
#
# Support for performing Term Frequency (TF) Inverse Document Frequency (IDF)
# using ngrams. This is provides a wrapper class around the tfidf package
# by elzilrac (https://github.com/elzilrac/tf-idf).
#
# For details on computations, see following Wikipedia pages:
#    https://en.wikipedia.org/wiki/Tf-idf
#    https://en.wikipedia.org/wiki/N-gram.
#
# Note:
# - This provides the wrapper class ngram_tfidf_analysis around tfidf for use
#   in applications like Visual Diff Search (VDS) that use text from external sources.
# - See compute_tfidf.py for computing tfidf over files.
#
# TODO2:
# - Find code that filters leading or trailing function words.
#
# TODO:
# - Add filtering (e.g., subsumption, all numbers).
# - Isolate ngram support into separate module.
# - Reconcile with compute_tfidf.py (e.g., subsumption here with overlap there).
#

"""TF-IDF using phrasal terms via ngram analysis

Examples:
  {script} -

  echo $'a b c\\nb c d\\nc d e' | MIN_NGRAM_SIZE=2 MAX_NGRAM_SIZE=2 SKIP_TFIDF_PREPROCESSOR=1 {script} {options} -
"""
## TODO: fix description (e.g., add pointer to VDS code)

# Standard packages
import re
import sys

# Installed packages
from sklearn.feature_extraction.text import CountVectorizer

# Local packages
from mezcla import debug
from mezcla import glue_helpers as gh
from mezcla.main import Main
from mezcla import system
from mezcla import tpo_common as tpo
from mezcla import tfidf
from mezcla.compute_tfidf import terms_overlap
from mezcla.text_processing import stopwords as ENGLISH_STOPWORDS
from mezcla.tfidf.corpus import Corpus as tfidf_corpus
from mezcla.tfidf.preprocess import Preprocessor as tfidf_preprocessor
from mezcla.tfidf import preprocess as tfidf_preprocess

SKIP_TFIDF_PREPROCESSOR = system.getenv_bool(
    "SKIP_TFIDF_PREPROCESSOR", False,
    description="Skip tf/idf prepreprocessing",
    )
DEFAULT_PREPROCESSOR_LANG = "english" if (not SKIP_TFIDF_PREPROCESSOR) else None
PREPROCESSOR_LANG = system.getenv_value(
    ## TODO3: standardize wrt TFIDF_LANGUAGE and STEMMER_LANGUAGE
    "PREPROCESSOR_LANG", DEFAULT_PREPROCESSOR_LANG,
    description="Language for ngram preprocessor")
# NOTE: MIN_NGRAM_SIZE (e.g., 2) is alternative to deprecated ALL_NGRAMS (implies 1)
MAX_NGRAM_SIZE = system.getenv_int("MAX_NGRAM_SIZE", 4)
# TODO: add descriptions to all getenv options
MIN_NGRAM_SIZE = system.getenv_int("MIN_NGRAM_SIZE", 2)
ALL_NGRAMS = system.getenv_boolean("ALL_NGRAMS", False)
USE_NGRAM_SMOOTHING = system.getenv_boolean("USE_NGRAM_SMOOTHING", False)
DEFAULT_TF_WEIGHTING = 'basic'
TF_WEIGHTING = system.getenv_text("TF_WEIGHTING", DEFAULT_TF_WEIGHTING)
DEFAULT_IDF_WEIGHTING = 'smooth' if USE_NGRAM_SMOOTHING else 'basic'
IDF_WEIGHTING = system.getenv_text("IDF_WEIGHTING", DEFAULT_IDF_WEIGHTING)
MAX_TERMS = system.getenv_int("MAX_TERMS", 100)
ALLOW_NGRAM_SUBSUMPTION = system.getenv_boolean("ALLOW_NGRAM_SUBSUMPTION", False,
                                                "Allow ngram subsumed by another--substring")
ALLOW_NGRAM_OVERLAP = system.getenv_boolean("ALLOW_NGRAM_OVERLAP", False,
                                            "Allows ngrams to overlap--token boundariese")
ALLOW_NUMERIC_NGRAMS = system.getenv_boolean("ALLOW_NUMERIC_NGRAMS", False)
DEFAULT_USE_CORPUS_COUNTER = (not tfidf_preprocess.USE_SKLEARN_COUNTER)
USE_CORPUS_COUNTER = system.getenv_boolean("USE_CORPUS_COUNTER", DEFAULT_USE_CORPUS_COUNTER,
                                           "Use slow tfidf package ngram tabulation")
TFIDF_BOOST_CAPITALIZED = system.getenv_boolean(
    "TFIDF_BOOST_CAPITALIZED", False,
    description="Treat capitalized ngrams higher others of same weight; excludes inner function words")

try:
    # Note major and minor revision values are assumed to be integral
    major_minor = re.sub(r"^(\d+\.\d+).*", r"\1", tfidf.__version__)
    TFIDF_VERSION = float(major_minor)
except:
    TFIDF_VERSION = 1.0
    system.print_stderr("Exception in main: " + str(sys.exc_info()))
assert(TFIDF_VERSION > 1.0)


class ngram_tfidf_analysis(object):
    """Class for performing TF-IDF over ngrams and returning sorted list"""

    def __init__(self, pp_lang=PREPROCESSOR_LANG, min_ngram_size=MIN_NGRAM_SIZE, max_ngram_size=MAX_NGRAM_SIZE, 
                 *args, **kwargs):
        """Class constructor: initialize corpus object (with PP_LANG, MIN_NGRAM_SIZE, and MAX_NGRAM_SIZE)"""
        # EX: ((self := ngram_tfidf_analysis(pp_lang="")) and (not self.pp.stopwords))
        # TODO: add option for stemmer; add all_ngrams and min_ngram_size to constructor
        debug.trace_fmtd(4, "ngram_tfidf_analysis.__init__(lang={pl}, min={minsz}, max={maxsz})",
                         pl=pp_lang, minsz=min_ngram_size, maxsz=max_ngram_size)
        debug.trace_fmtd(5, "\targs={a} kwargs={k}", a=args, k=kwargs)
        if pp_lang is None:
            pp_lang = PREPROCESSOR_LANG
        self.min_ngram_size = min_ngram_size
        self.max_ngram_size = max_ngram_size
        self.pp = tfidf_preprocessor(language=pp_lang,
                                     gramsize=self.max_ngram_size,
                                     min_ngram_size=self.min_ngram_size,
                                     all_ngrams=ALL_NGRAMS,
                                     stemmer=lambda x: x)
        self.corpus = tfidf_corpus(gramsize=self.max_ngram_size,
                                   min_ngram_size=self.min_ngram_size,
                                   all_ngrams=ALL_NGRAMS,
                                   language=pp_lang,
                                   preprocessor=self.pp)
        ## TODO2: add international stopwords (e.g., English plus frequent ones from common languages)
        self.stopwords = (self.pp.stopwords or ENGLISH_STOPWORDS)
        super().__init__(*args, **kwargs)

    def add_doc(self, text, doc_id=None):
        """Add document TEXT to collection with key DOC_ID, which defaults to order processed (1-based)"""
        if doc_id is None:
            doc_id = str(len(self.corpus) + 1)
        self.corpus[doc_id] = text

    def get_doc(self, doc_id):
        """Return document data for DOC_ID"""
        return self.corpus[doc_id]

    def is_stopword(self, word):
        """Whether WORD is a stop word for preprocessing language or English if none"""
        # EX: self.is_stopword("of")
        # EX: ngram_tfidf_analysis(pp_lang="spanish").is_stopword("de")
        result = word in self.stopwords
        debug.trace(8, f"is_stopword({word!r}) => {result}")
        return result

    def capitalized_ngram(self, ngram):
        """Whethere NGRAM is capitalized, excepting internal stopwords"""
        ## EX: self.capitalized_ngram("House of Cards")
        ## EX: not self.capitalized_ngram("in New York")
        tokens = ngram.split()
        result = (tokens and tokens[0].istitle()
                  and ((len(tokens) == 1) or tokens[-1].istitle()))
        if (result and (len(tokens) > 2)):
            for w in tokens[1: -1]:
                if not (w.istitle() or self.is_stopword(w)):
                    debug.trace(5, f"ngram with lower inner non-stop word {w!r}: {tokens!r}")
                    result = False
                    break
        debug.trace(7, f"capitalized_ngram({ngram!r}) => {result}")
        return result
    
    def get_top_terms(self, doc_id, tf_weight=TF_WEIGHTING, idf_weight=IDF_WEIGHTING, limit=MAX_TERMS,
                      allow_ngram_subsumption=ALLOW_NGRAM_SUBSUMPTION,
                      allow_ngram_overlap=ALLOW_NGRAM_OVERLAP, allow_numeric_ngrams=ALLOW_NUMERIC_NGRAMS):
        """Return list of (term, weight) tuples for DOC_ID up to LIMIT count, using TF_WEIGHT and IDF_WEIGHT schemes
        Notes:
        - TF_WEIGHT in {basic, binary, freq, log, norm_50}
        - IDF_WEIGHT in {basic freq, max, prob, smooth}
        - The top ngrams omit blanks and other relics of tokenization
        - Lower weighted ngrams are omitted if subsumed by higher (or vice versa) unless ALLOW_NGRAM_SUBSUMPTION;
          likewise, in the case of ngram overlap unless ALLOW_NGRAM_OVERLAP
        """
        # Get objects for top terms
        # ex: top_terms=[CorpusKeyword(term=<tfidf.dockeyword.DocKeyword object at 0x7f08b43bf550>, ngram=u'patuxent river', score=0.0015548719642054984), ... CorpusKeyword(term=<tfidf.dockeyword.DocKeyword object at 0x7f08b43cf110>, ngram=u'afognak native corporation', score=0.0009894639772216809)]
        # Get twice as many top terms to display to account for filtering
        # TODO: keep track of how often too few terms shown
        debug.trace(6, (f"get_top_terms({doc_id}, tfw:{tf_weight}, idfw:{idf_weight}, lim={limit},"
                        f"allow_sub={allow_ngram_subsumption}, allow_over={allow_ngram_overlap},"
                        f"allow_num={allow_numeric_ngrams})"))
        top_terms = self.corpus.get_keywords(document_id=doc_id,
                                             tf_weight=tf_weight,
                                             idf_weight=idf_weight,
                                             limit=(2 * limit))
        debug.trace_fmtd(7, "top_terms={tt}", tt=top_terms)

        # Skip empty tokens due to spacing and to punctuation removal (e.g, " ")
        top_term_info = [(k.ngram, k.score) for k in top_terms if k.ngram.strip()]
        debug.trace_values(6, top_term_info, "init top terms")

        # Move capitalized terms ahead of others with same weight
        # Note: allows for inner non-capitalized only if functions words
        for (j, (ngram, score)) in enumerate(reversed(top_term_info)):
            if (TFIDF_BOOST_CAPITALIZED and (j > 0) and self.capitalized_ngram(top_term_info[j][0])
                and (top_term_info[j][1] == top_term_info[j - 1][1])):
                top_term_info[j - 1], top_term_info[j] = top_term_info[j], top_term_info[j - 1]
                debug.trace(5, f"moved capitalized ngram '{top_term_info[j - 1]}' up in list from {j} to {j - 1}")
        debug.trace_values(6, top_term_info, "interim top terms")
        
        # Put spaces around ngrams to aid in subsumption tests
        check_ngram_overlap = (not (allow_ngram_subsumption and allow_ngram_overlap))
        if check_ngram_overlap:
            spaced_ngrams = [(" " + ngram + " ") for (ngram, _score) in top_term_info]
            debug.trace_fmtd(7, "spaced_ngrams={sn}", sn=spaced_ngrams)
        final_top_term_info = []
        for (i, (ngram, score)) in enumerate(top_term_info):
            
            if (not ngram.strip()):
                debug.trace_fmt(6, "Omitting invalid ngram '{ng}'", ng=ngram)
                continue
            if ((not allow_numeric_ngrams) and any(tpo.is_numeric(token) for token in ngram.split())):
                debug.trace_fmt(6, "Omitting ngram with numerics '{ng}'", ng=ngram)
                continue
            
            # Check for subsumption (e.g., "new york" in "new york city") and overlap (e.g. "new york" and "york city")
            ## TODO: record ngram offsets to facilitate contiguity tests
            include = True
            if check_ngram_overlap:
                for (j, other_spaced_ngram) in enumerate(spaced_ngrams):
                    is_subsumed = ((not allow_ngram_subsumption) and
                                   ((spaced_ngrams[i] in other_spaced_ngram)
                                     or (other_spaced_ngram in spaced_ngrams[i])))
                    has_overlap = ((not allow_ngram_overlap) and
                                   terms_overlap(spaced_ngrams[i], other_spaced_ngram))
                    if ((i > j) and (is_subsumed or has_overlap)):
                        include = False
                        label = ("in subsumption" if is_subsumed else "overlapping")
                        debug.trace_fmt(6, "Omitting lower-weigted ngram '{ng2}' {lbl} with '{ng1}': {s1} <= {s2}",
                                        ng1=other_spaced_ngram.strip(), ng2=spaced_ngrams[i].strip(), lbl=label,
                                        s1=system.round_num(top_term_info[i][1]), s2=system.round_num(top_term_info[j][1]))
                        break
            if not include:
                continue

            # OK
            final_top_term_info.append((ngram, score))
            if (len(final_top_term_info) == limit):
                break
        debug.trace_values(6, final_top_term_info, "final top terms")

        # Sanity check on number of terms displayed
        num_terms = len(final_top_term_info)
        if (num_terms < limit):
            debug.trace_fmt(4, "Warning: only {n} terms shown (of {m} max)",
                            n=num_terms, m=limit)
        debug.trace_fmtd(6, "final_top_term_info={tti}", tti=final_top_term_info)
        return final_top_term_info

    def old_get_ngrams(self, text):
        """Returns generator with ngrams in TEXT"""
        ## NOTE: Now returns the ngrams
        ngrams = []
        gen = self.pp.yield_keywords(text)
        more = True
        while (more):
            ## DEBUG: debug.trace_fmtd(6, ".")
            try:
                ngrams.append(next(gen).text)
            except StopIteration:
                more = False
        debug.trace_fmt(6, "ngram_tfidf_analysis.old_get_ngrams({t}) [self={s}] => {nl}", 
                        t=text, s=self, nl=ngrams)
        return ngrams

    def get_ngrams(self, text):
        """Returns ngrams in TEXT (from size MIN_NGRAM_SIZE to MAX_NGRAM_SIZE)"""
        # Based on https://stackoverflow.com/questions/13423919/computing-n-grams-using-python.
        if USE_CORPUS_COUNTER:
            return self.old_get_ngrams(text)
        if self.corpus:
            debug.trace(6, "Note: not using tfidf corpus object")
        vectorizer = CountVectorizer(ngram_range=(self.min_ngram_size, self.max_ngram_size))
        analyzer = vectorizer.build_analyzer()
        ngram_list = analyzer(text)
        debug.trace_fmt(6, "ngram_tfidf_analysis.get_ngrams({t}) [self={s}] => {nl}", 
                        t=text, s=self, nl=ngram_list)
        return ngram_list

def simple_main_test():
    """Run test extracting ngrams from this source file"""
        # Tabulate ngram occurrences
    ## BAD: ngram_analyzer = ngram_tfidf_analysis(min_ngram_size=2, max_ngram_size=3)
    ngram_analyzer = ngram_tfidf_analysis(min_ngram_size=MIN_NGRAM_SIZE, max_ngram_size=MAX_NGRAM_SIZE)
    all_text = system.read_entire_file(__file__)
    all_ngrams = ngram_analyzer.get_ngrams(all_text)
    reversed_all_text = " ".join(list(reversed(all_text.split())))
    ngram_analyzer.add_doc(all_text, doc_id="doc1")
    ngram_analyzer.add_doc(reversed_all_text, doc_id="rev-doc1")
    top_ngrams = ngram_analyzer.get_top_terms("rev-doc1", allow_ngram_subsumption=False, allow_ngram_overlap=False)

    # Check for common ngrams
    debug.assertion("simple test follows" in all_ngrams)
    debug.assertion("system getenv_boolean" in top_ngrams)
    debug.assertion("system" not in all_ngrams)
    debug.assertion("getenv_boolean" not in all_ngrams)
    
    # Check for filtering based on subsumption and overlap
    debug.assertion("warning not" in top_ngrams)
    debug.assertion("warning not intended" not in top_ngrams)

    # Check for tf/idf values
    # TODO: add assertion for specific tfidf values
    try:
        debug.assertion(ngram_analyzer.corpus.tf_idf("system getenv_boolean", document_id="doc1")
                        == ngram_analyzer.corpus.tf_idf("getenv_boolean system", document_id="rev-doc1"))
    except:
        system.print_exception_info("corpus.tf_idf")

    # Output ngram sample
    SAMPLE_SIZE = 10
    init_ngram_spec = "\n\t".join(all_ngrams[:SAMPLE_SIZE])
    print(f"first 10 ngrams in {__file__}:\n\t{init_ngram_spec}")
    init_top_ngram_spec = "\n\t".join([f"{t}: {tpo.round_num(s, 3)}"
                                       for (t, s) in top_ngrams[:SAMPLE_SIZE]])
    print(f"top ngrams in {__file__}:\n\t{init_top_ngram_spec}")


def output_tfidf_analysis(main_app):
    """Output results for ngram TF/IDF analysis over input from MAIN_APP"""
    ngram_analyzer = ngram_tfidf_analysis(min_ngram_size=MIN_NGRAM_SIZE, max_ngram_size=MAX_NGRAM_SIZE)
    all_text = main_app.read_entire_input()
    num_docs = 0
    for l, line in enumerate(all_text.splitlines()):
        ngram_analyzer.add_doc(line, doc_id=(l + 1))
        num_docs += 1

    # Output ngram sample
    SAMPLE_SIZE = 10
    for l in range(num_docs):
        top_ngrams = ngram_analyzer.get_top_terms(l + 1)
        top_ngram_spec = "; ".join([f"{t}: {tpo.round_num(s, 3)}"
                                    for (t, s) in top_ngrams[:SAMPLE_SIZE]])
        print(f"{l}\t{top_ngram_spec}")
    
def main():
    """Entry point for script"""
    SIMPLE_TEST_OPT = "simple-test"
    REGULAR_OPT = "regular"
    main_app = Main(description=__doc__.format(script=gh.basename(__file__),
                                               options=f"--{REGULAR_OPT}"),
                    boolean_options=[(SIMPLE_TEST_OPT, "Run simple test (default)"),
                                     (REGULAR_OPT, "Process regular input")],
                    skip_input=False)
    regular = main_app.get_parsed_option(REGULAR_OPT)
    simple_test = main_app.get_parsed_option(SIMPLE_TEST_OPT, not regular)
    if (simple_test):
        simple_main_test()
    else:
        output_tfidf_analysis(main_app)
   
#-------------------------------------------------------------------------------

if __name__ == '__main__':
    main()
