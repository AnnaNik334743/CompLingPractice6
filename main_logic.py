from pymystem3 import Mystem
from navec import Navec
import wget
import numpy as np
import matplotlib.pyplot as plt
import os
import pickle

mystem = Mystem()

navecname = 'navec_hudlit_v1_12B_500K_300d_100q.tar'
if navecname not in os.listdir():
    wget.download(f'https://storage.yandexcloud.net/natasha-navec/packs/{navecname}')
navec = Navec.load(navecname)

model = pickle.load(open('best_model', 'rb'))

# https://yandex.ru/dev/mystem/doc/grammemes-values.html
possible_tags = ['ADVPRO',  # местоименное наречие
                 'ANUM',  # числительное-прилагательное
                 'APRO',  # местоимение-прилагательное
                 'ADV',  # наречие
                 'PART',  # частица
                 'A',  # прилагательное
                 'SPRO',  # местоимение-существительное
                 'CONJ',  # союз
                 'INTJ',  # междометие
                 'COM',  # часть композита - сложного слова
                 'NUM',  # числительное
                 'PR',  # предлог
                 'S',  # существительное
                 'V']  # глагол

verb_time = ['наст',  # настоящее
             'непрош',  # будущее
             'прош']  # прошедшее

rare = 'редк'
parenth = 'вводн'

# список далеко не полный, но хоть что-то
s_conjs = ['и', 'да', 'a', 'но', 'тоже', 'также', 'или', 'либо', 'зато', 'однако']
p_conjs = ['что', 'чтобы', 'как', 'когда', 'ибо', 'пока', 'будто', 'словно',
           'если', 'кто', 'который', 'какой', 'где', 'куда', 'откуда']

punct = ['.', '!', '?', '...', '?..', '!..', ',', ';', ':']

colnames = {el: i for i, el in enumerate(['ADVPRO', 'ANUM', 'APRO', 'ADV', 'PART',
                                          'A', 'SPRO', 'CONJ_S', 'CONJ_P', 'INTJ',
                                          'COM', 'NUM', 'PR', 'S', 'V', 'V_наст', 'V_непрош',
                                          'V_прош', 'редк', 'вводн', '.', '!', '?',
                                          '...', '?..', '!..', ',', ';', ':'])}


def text2vec(text: str = '', return_lemmatized: bool = False):
    """Переводит текст (предложение) в вектор. Использует в работе глобальные переменные.

    Идея: каждый текст преобразуется в вектор. Вектор состоит из двух частей -
    "статистического вектора" и "смыслового вектора". Статистический вектор усредняется путем
    деления на свою длину и содержит в себе информацию о:
    * количестве различных частей речи. Для глаголов также указывается их время (если определено), а для союзов - тип
    * количество редких слов
    * количество вводных слов
    * количество различных знаков препенания, использующихся в качестве окончания предложений
    Смысловой вектор содержит в себе сумму значений из предобученного word2vec (navec на 500К слов из проекта natasha)
    по всем словам, которые несут смысловую информацию, т.е. знаки препинания сюда не входят.
    Вектор усредняется путем деления на кол-во слагаемых, составляющих его."""

    analysis = mystem.analyze(text)
    stats_vec = np.zeros(len(colnames))
    word2vec_vec = np.zeros(300)
    n_word2vec = 0
    norm_text = []
    not_known = 0
    known = 0

    for item in analysis:
        word = item['text'].lower().replace('\n', ' ').strip()
        try:
            analysis = item['analysis'][0]
        except (IndexError, KeyError):
            analysis = None

        if analysis is not None:
            known += 1
            word2vec_vec += navec[word] if word in navec else navec['<unk>']
            n_word2vec += 1

            norm_form = analysis['lex']  # нормальная форма
            norm_text.append(norm_form)
            grammar = analysis['gr']  # морфология
            for tos in possible_tags:
                if grammar.find(rare) != -1:
                    stats_vec[colnames[rare]] += 1
                if grammar.find(parenth) != -1:
                    stats_vec[colnames[parenth]] += 1
                if grammar.find(tos) != -1:
                    if tos == 'V':
                        for tm in verb_time:
                            if grammar.find(tm) != -1:
                                stats_vec[colnames[f'V_{tm}']] += 1
                                break
                        else:
                            stats_vec[colnames[tos]] += 1
                    elif tos == 'CONJ':
                        if item['text'].lower() in s_conjs:
                            stats_vec[colnames['CONJ_S']] += 1
                        else:
                            stats_vec[colnames['CONJ_P']] += 1
                    else:
                        stats_vec[colnames[tos]] += 1
                    break
        else:
            if word in punct:
                stats_vec[colnames[word]] += 1
            elif not (word.isspace() or len(word) == 0):
                not_known += 1

    stats_vec /= len(stats_vec)  # нормализация векторов
    word2vec_vec = word2vec_vec / n_word2vec if n_word2vec != 0 else word2vec_vec

    vec = np.hstack((stats_vec, word2vec_vec))  # объединение "статистического" и "смыслового" векторов

    if not_known > 0.7 * known:  # если слишком много незнакомых слов
        raise TypeError

    if return_lemmatized:
        return vec, ' '.join(norm_text)
    return vec


def get_pred(text: str = ''):
    """Относитель удобный интерфейс для вывода
    предсказанного класса и его вероятности"""
    global model

    inner = [text2vec(text)]
    classes = model.classes_
    probs = model.predict_proba(inner)[0]
    pred = classes[np.argmax(probs)]

    x = list(map(lambda t: t.capitalize(), classes))
    colors = ['#FFC09F', '#D3DFB8', '#C3ACCE']
    percent = 100.*probs
    patches, texts = plt.pie(probs, colors=colors, startangle=90, radius=1.2,
                             wedgeprops={'edgecolor': '#F8F8FF', 'linewidth': 2, 'antialiased': True})
    labels = ['{0} - {1:1.2f} %'.format(i, j) for i, j in zip(x, percent)]
    plt.legend(patches, labels, loc='best', fontsize=12)
    plt.savefig('images/pie.jpg')

    return pred.capitalize()
