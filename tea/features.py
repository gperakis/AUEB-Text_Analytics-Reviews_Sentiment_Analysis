import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from tea.load_data import parse_reviews
from tea import setup_logger, NEGATIVE_WORDS, POSITIVE_WORDS
from tea.text_mining import tokenize_text
from tea.word_embedding import WordEmbedding
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from tqdm import tqdm

logger = setup_logger(__name__)


class ModelTransformer(BaseEstimator, TransformerMixin):

    def __init__(self, model):
        self.model = model

    def fit(self, *args, **kwargs):
        self.model.fit(*args, **kwargs)
        return self

    def transform(self, X, **transform_params):
        return pd.DataFrame(self.model.predict(X))


class ColumnExtractor(BaseEstimator, TransformerMixin):
    """Takes in dataframe, extracts a number of columns and return these columns"""

    def __init__(self, columns):
        """

        :param columns:
        """
        self.columns = columns

    def transform(self, X, y=None):

        if set(self.columns).issubset(set(X.columns.tolist())):
            return X[self.columns].values

        else:
            raise Exception('Columns declared, not in dataframe')

    def fit(self, X, y=None):
        """Returns `self` unless something different happens in train and test"""

        return self


class TextColumnExtractor(BaseEstimator, TransformerMixin):
    """Takes in dataframe, extracts the column with the text"""

    def __init__(self, column):
        """

        :param column:
        """
        self.column = column

    def transform(self, X, y=None):

        if {self.column}.issubset(set(X.columns.tolist())):
            return X[self.column]

        else:
            raise Exception('Columns declared, not in dataframe')

    def fit(self, X, y=None):
        """Returns `self` unless something different happens in train and test"""

        return self


class DenseTransformer(BaseEstimator, TransformerMixin):

    def transform(self, X, y=None, **fit_params):
        return X.todense()

    def fit_transform(self, X, y=None, **fit_params):
        self.fit(X, y, **fit_params)
        return self.transform(X)

    def fit(self, X, y=None, **fit_params):
        return self


class SingleColumnDimensionReshaper(BaseEstimator, TransformerMixin):

    def __init__(self):
        """

        """
        pass

    def transform(self, X, y=None):
        return X.values.reshape(-1, 1)

    def fit(self, X, y=None):
        """Returns `self` unless something different happens in train and test"""

        return self


class WordLengthMetricsExtractor(BaseEstimator, TransformerMixin):
    """Takes in dataframe, extracts text column, splits text in tokens and outputs average word length"""

    def __init__(self,
                 col_name,
                 split_type='simple',
                 metric='avg'):
        """

        :param split_type:
        """
        assert metric in ['avg', 'std']
        self.split_type = split_type
        self.col_name = col_name
        self.metric = metric

    def calculate_metric(self, words):
        """
        Helper code to compute average word length of a name
        :param words:
        :return:
        """
        if words:
            if self.metric == 'avg':
                return np.mean([len(word) for word in words])

            elif self.metric == 'std':
                return np.std([len(word) for word in words])

        else:
            return 0

    def transform(self, X, y=None):

        logger.info('Calculating {} for "{}" Column'.format(self.metric, self.col_name))
        x = X[self.col_name].apply(lambda s: tokenize_text(text=s, split_type=self.split_type))

        return x.apply(self.calculate_metric)

    def fit(self, X, y=None):
        """Returns `self` unless something different happens in train and test"""
        return self


class TextLengthExtractor(BaseEstimator, TransformerMixin):
    """Takes in dataframe, extracts text column, returns sentence's length"""

    def __init__(self, col_name):
        """

        :param col_name:
        """
        self.col_name = col_name

    def transform(self, X, y=None):
        logger.info('Calculating text length for "{}" Column'.format(self.col_name))
        return X[self.col_name].apply(len)

    def fit(self, X, y=None):
        """Returns `self` unless something different happens in train and test"""
        return self


class ContainsSpecialCharactersExtractor(BaseEstimator, TransformerMixin):
    def __init__(self, col_name):
        """
        This class checks whether there are some given special characters in a text.
        :param col_name:
        """
        self.col_name = col_name
        self.SPECIAL_CHARACTERS = set("!@#$%^&*()_+-=")

    def transform(self, X, y=None):
        logger.info('Checking whether text contains special characters for "{}" Column'.format(self.col_name))

        return X[self.col_name].apply(lambda s: bool(set(s) & self.SPECIAL_CHARACTERS))

    def fit(self, X, y=None):
        """Returns `self` unless something different happens in train and test"""
        return self


class ContainsUppercaseWords(BaseEstimator, TransformerMixin):
    """Takes in data-frame, extracts number of tokens in text"""

    def __init__(self, col_name=None, how='bool'):
        """

        :param col_name:
        :param how:
        """
        assert how in ['bool', 'count']
        self.col_name = col_name
        self.how = how

    def calculate_uppercase_words_in_tokens(self, sentence):
        """
        This method checks whether we have words writter with uppercase chararcters in a sentence.
        :param sentence:
        :param how:
        :return:
        """
        tokens = tokenize_text(text=sentence, split_type='simple')

        if self.how == 'bool':
            for t in tokens:
                if t.isupper():
                    return True
            return False

        else:
            return sum([1 for token in tokens if token.isupper()])

    def transform(self, X, y=None):

        if self.col_name is None:
            logger.info('Checking if text contains uppercase words for pandas series')
            return X.apply(self.calculate_uppercase_words_in_tokens)

        logger.info('Checking if text contains uppercase words for "{}" Column'.format(self.col_name))
        return X[self.col_name].apply(self.calculate_uppercase_words_in_tokens)

    def fit(self, X, y=None):
        """Returns `self` unless something different happens in train and test"""
        return self


class NumberOfTokensCalculator(BaseEstimator, TransformerMixin):
    """Takes in dataframe, extracts number of tokens in text"""

    def __init__(self, col_name):
        """
        :param col_name:
        """
        self.col_name = col_name

    def transform(self, X, y=None):
        logger.info('Counting number of tokens for "{}" Column'.format(self.col_name))
        return X[self.col_name].apply(lambda x: len(tokenize_text(x, split_type='thorough')))

    def fit(self, X, y=None):
        """Returns `self` unless something different happens in train and test"""
        return self


class HasSentimentWordsExtractor(BaseEstimator, TransformerMixin):
    """Takes in data-frame, extracts number of tokens in text"""

    def __init__(self,
                 col_name,
                 count_type='boolean',
                 input_type='text',
                 sentiment='negative'):
        """
        :param col_name:
        """
        assert sentiment in ['negative', 'positive']
        assert count_type in ['boolean', 'counts']
        assert input_type in ['text', 'tokens']

        self.col_name = col_name
        self.sentiment = sentiment
        self.input_type = input_type
        self.count_type = count_type

        if self.sentiment == 'positive':

            self.words_set = POSITIVE_WORDS
        else:
            self.words_set = NEGATIVE_WORDS

    def calculate_boolean_output(self, inp):
        """
        This method checks whether a sentence contains at least one tokens that contains sentiment.

        :param inp:
        :return:
        """
        tokens = inp.split() if self.input_type == 'text' else inp

        for token in set(tokens):
            if token in self.words_set:
                return True

        return False

    def calculate_counts_output(self, inp):
        """
        This method counts the number of tokens that contain sentiment in a text.
        :param inp:
        :return:
        """
        tokens = inp.split() if self.input_type == 'text' else inp

        return sum([1 for t in tokens if t in self.words_set])

    def transform(self, X, y=None):
        """

        :param X:
        :param y:
        :return:
        """

        logger.info('Searching for {} sentiment of tokens for "{}" Column'.format(self.sentiment, self.col_name))

        if self.count_type == 'boolean':
            return X[self.col_name].apply(self.calculate_boolean_output)

        else:
            return X[self.col_name].apply(self.calculate_counts_output)

    def fit(self, X, y=None):
        """Returns `self` unless something different happens in train and test"""
        return self


class AverageSentenceEmbedding(BaseEstimator, TransformerMixin):
    """Takes in dataframe, the average of sentence's word embeddings"""

    def __init__(self,
                 col_name=None,
                 embedding_type='tf',
                 embedding_dimensions=200):
        """

        :param col_name:
        :param embedding_type:
        :param embedding_dimensions:
        """
        assert embedding_type in ['tf', 'tfidf']

        self.col_name = col_name
        self.word_embeddings = WordEmbedding.get_word_embeddings(dimension=embedding_dimensions)
        self.embedding_type = embedding_type

    def calculate_sentence_word_embedding(self, sentence):
        """

        :param sentence:
        :return:
        """
        if self.embedding_type == 'tf':
            sum_w_e = 0

            for token in sentence.split():
                sum_w_e += np.mean(self.word_embeddings.get(token, [0]))

            return sum_w_e / len(sentence.split())

        elif self.embedding_type == 'tfidf':
            raise NotImplementedError()

    def calculate_word_embeddings(self, X):
        """

        :param X:
        :return:
        """

        if self.embedding_type == 'tf':

            vectorizer = CountVectorizer(strip_accents='unicode',
                                         analyzer='word',
                                         ngram_range=(1, 1),
                                         stop_words=None,
                                         lowercase=True,
                                         binary=False)

        elif self.embedding_type == 'tfidf':

            vectorizer = TfidfVectorizer(strip_accents='unicode',
                                         analyzer='word',
                                         ngram_range=(1, 1),
                                         stop_words=None,
                                         lowercase=True,
                                         binary=False,
                                         norm='l2',
                                         use_idf=True,
                                         smooth_idf=True)

        else:
            raise NotImplementedError()

        X_transformed = vectorizer.fit_transform(X)

        analyser = vectorizer.build_analyzer()
        vocabulary_indices = vectorizer.vocabulary_

        centroid_values_updated = list()

        for index_row, doc in enumerate(tqdm(X, unit=' Document')):
            sum_w_e = 0

            # breaks test in tokens.
            doc_tokens = analyser(doc)

            # We keep only the unique ones in order to get the tf-idf values from the stored matrix X_transformed.
            for token in set(doc_tokens):

                # get column index from the vocabulary in order to find the exact spot in the X_transformed matrix
                index_col = vocabulary_indices[token]

                # Getting the tf or idf value for the given word from the transformed matrix
                token_tf_or_idf_value = X_transformed[index_row, index_col]

                # Calculating the mean (centroid) value of the vector
                mean_token_value = np.mean(self.word_embeddings.get(token, [0]))

                # Getting the product of the idf and centroid
                sum_w_e += (token_tf_or_idf_value * mean_token_value)

            doc_final_value = sum_w_e / len(doc_tokens)
            centroid_values_updated.append(doc_final_value)

        return np.array(centroid_values_updated)

    def transform(self, X, y=None):

        if self.col_name is None:
            logger.info('Calculating word embeddings of sentences for pandas series')
            # return X.apply(lambda x: self.calculate_sentence_word_embedding(x))
            return self.calculate_word_embeddings(X=X)

        logger.info('Calculating word embeddings of sentences for "{}" Column'.format(self.col_name))
        # return X[self.col_name].apply(lambda x: self.calculate_sentence_word_embedding(x))
        return self.calculate_word_embeddings(X=X[self.col_name])

    def fit(self, X, y=None):
        """Returns `self` unless something different happens in train and test"""
        return self


if __name__ == "__main__":

    mydata = parse_reviews(load_data=True, save_data=True)

    obj = AverageSentenceEmbedding(embedding_dimensions=50,
                                   col_name='text',
                                   embedding_type='tfidf')

    doc_embeddings = obj.fit_transform(X=mydata)

    print(doc_embeddings)