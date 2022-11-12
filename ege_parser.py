import requests
from bs4 import BeautifulSoup
import re
import typing as tp


"""В ЕГЭ по русскому языку присутствует задание на ФСТР (функционально-смысловые типы речи). 
Задание относится к тестовым и в 2022 году фигурирует под номером 23. 
В нем требуется прочитать текст с пронумерованными предложениями и ответить на 5 вопросов 
(либо отметить верные, либо отметить ошибочные утверждения).
Среди вопросов встречаются вопросы типа "В предложениях 3—7 представлено рассуждение". 
Именно подобный тип парсится для данной задачи.

Сайт: https://rus-ege.sdamgia.ru/"""


def invert(num: str, total: int = 5):
    """Если в условии присутствует "найти ошибочные пункты",
    то нужно инвертировать ответ"""
    output = ''
    for n in range(1, total+1):
        if not str(n) in num:
            output += str(n)
    return output


def correct_questions(questions: tp.List[str], answers_num: str, total: int = 5):
    """Выделение из общего списка вопросов, на которые дан
    положительный ответ"""
    correct = []
    for num in answers_num:
        num = int(num)
        if num < total:
            correct.append(re.search(f"{num}\)(.*){num+1}\)", questions)[1].lower())
        else:
            correct.append(re.search(f"{num}\)(.*)", questions)[1].lower())
    return correct


def get_sentence_numbers(sentence: str):
    """Выделение из ответов интервалов/отдельных предложений как чисел"""
    lst = set()
    intervals = re.findall(r'\d+–\d+', sentence)
    for interval in intervals:
        start, end = interval.split('–')
        for i in range(int(start), int(end)+1):
            lst.add(i)
    alone = re.findall(r'\d+', sentence)
    for al in alone:
        lst.add(int(al))
    return sorted(list(lst))


def get_sentence(sent_num: int, text: str):
    """Выделение из общего текста предложений под определенными номерами"""
    try:
        sentence = re.search(f"\({sent_num}\)(.*)\({sent_num+1}\)", text)[1]
    except TypeError:
        sentence = re.search(f"\({sent_num}\)(.*)\(\D", text)[1]
    return sentence


if __name__ == '__main__':

    website = 'https://rus-ege.sdamgia.ru'
    problem_links = []

    for theme in [230, 313, 283]:  # все доступные 23-и задания на поиск ФСТР
        page = requests.get(website + f'/test?theme={theme}&print=true')
        soup = BeautifulSoup(page.text, 'html.parser')
        for found in soup.findAll('span', {'class': 'prob_nums'}):
            problem_links.append(found.a['href'])

    pov = []
    op = []
    ras = []

    for problem_link in problem_links:

        try:  # несмотря на то, что задания максимально унифицированы, иногда бывают приколы
            task_link = website + problem_link
            task_page = requests.get(task_link)
            task_soup = BeautifulSoup(task_page.text, 'html.parser')

            id_ = re.search(r'problem\?id=(.*)', task_link)[1]

            questions = task_soup.find('div', {'align': 'justify', 'class': 'pbody'}).text
            questions = questions.replace('\u202f', '').replace('\xa0', '')

            paragraphs = task_soup.findAll('div', {'id': f'text{id_}'})[0]
            text = paragraphs.text
            text = text.replace('\u202f', '').replace('\xa0', '')

            answers = task_soup.findAll('div', {'id': f'sol{id_}'})[0].text
            answers_num = re.search(r'Ответ:(.*)', answers)[1].split('|')[0]
            answers_num = ''.join(list(filter(lambda s: s.isdigit(), answers_num)))

            init_question = questions.split('?')[0].lower()
            if 'неверными' in init_question or 'ошибочными' in init_question or ' не ' in init_question:
                answers_num = invert(answers_num)

            questions_with_yes = correct_questions(questions, answers_num)

            for question in questions_with_yes:
                for item in ['не ', 'нет', 'неверно', 'неправильно', 'некорректно', 'ошибочно', 'элементами']:
                    if question.find(item) != -1:
                        break
                else:
                    sentence_numbers = get_sentence_numbers(question)
                    new_text = []
                    for sent_num in sentence_numbers:
                        new_text.append(get_sentence(sent_num, text).strip())
                    new_text = ' '.join(new_text)

                    if question.find('повествование') != -1:
                        pov.append(new_text)
                    elif question.find('описание') != -1:
                        op.append(new_text)
                    elif question.find('рассуждение') != -1:
                        ras.append(new_text)

        except TypeError:
            continue

    # запись полученных данных в файл
    with open('ege23task.txt', mode='w', encoding='utf-8') as file:
        file.write('ПОВЕСТВОВАНИЕ\n\n')
        file.write('\n\n'.join(pov))
        file.write('\n\nОПИСАНИЕ\n\n')
        file.write('\n\n'.join(op))
        file.write('\n\nРАССУЖДЕНИЕ\n\n')
        file.write('\n\n'.join(ras))
