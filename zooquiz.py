import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv, find_dotenv
from aiogram.utils.exceptions import ChatNotFound

from data import questions, pictures

load_dotenv(find_dotenv())

# Загрузка переменных окружения
API_TOKEN = os.getenv('API_TOKEN')  # Измените на ваше имя переменной

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# Для хранения очков пользователя
user_scores = {}

# Клавиатура с кнопками
def get_keyboard(options):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for option in options:
        keyboard.add(KeyboardButton(option))
    return keyboard

# Начало викторины
@dp.message_handler(commands=['start'])
async def start_quiz(message: types.Message):
    user_scores[message.from_user.id] = {}
    user_first_name = message.from_user.first_name
    greeting_message = f"Привет, {user_first_name}! Давай выясним, какое ты животное в Московском зоопарке! Отвечай на вопросы:"
    image_path = 'jmg/MZoo-logo-hor-mono-white-rus-preview-RGB.jpg'
    await bot.send_photo(message.chat.id, photo=InputFile(image_path))
    await bot.send_message(message.chat.id, greeting_message)
    await ask_question(message, 0)

# Функция для отправки вопроса
async def ask_question(message: types.Message, question_idx: int):
    question = questions[question_idx]
    await bot.send_message(message.chat.id, question["text"], reply_markup=get_keyboard(question["options"]))

# Обработка ответов
@dp.message_handler(lambda message: message.text in [option for question in questions for option in question['options']])
async def handle_answer(message: types.Message):
    user_id = message.from_user.id
    answer = message.text

    if user_id not in user_scores:
        user_scores[user_id] = {}

    for idx, question in enumerate(questions):
        if answer in question["options"]:
            for animal, score in question["scores"].items():
                if animal not in user_scores[user_id]:
                    user_scores[user_id][animal] = 0
                if answer == question["options"][list(question["scores"].keys()).index(animal)]:
                    user_scores[user_id][animal] += score

            if idx + 1 < len(questions):
                await ask_question(message, idx + 1)
            else:
                await show_result(message)
            break

# Функция показа результатов
async def show_result(message: types.Message):
    user_id = message.from_user.id
    scores = user_scores[user_id]
    best_animal = max(scores, key=scores.get)

    result_text = f"Твоё тотемное животное — {best_animal}!"
    await bot.send_photo(chat_id=message.chat.id, photo=pictures[best_animal], caption=result_text)

    # Отправка кнопок
    keyboard = get_keyboard([
        "Поделиться результатом",
        "Узнать о программе опеки",
        "Связаться с сотрудником",
        "Оставить отзыв",
        "Попробовать ещё раз?",
        "Назад"
    ])

    await bot.send_message(message.chat.id, "Выберите одно из действий:", reply_markup=keyboard)

# Обработка нажатия кнопки "Назад"
@dp.message_handler(lambda message: message.text == "Назад")
async def go_back(message: types.Message):
    # Отправка кнопок выбора действий
    keyboard = get_keyboard([
        "Поделиться результатом",
        "Узнать о программе опеки",
        "Связаться с сотрудником",
        "Оставить отзыв",
        "Попробовать ещё раз?"
    ])

    await message.answer("Выберите одно из действий:", reply_markup=keyboard)


# Обработка перезапуска викторины
@dp.message_handler(lambda message: message.text == "Попробовать ещё раз?")
async def restart_quiz(message: types.Message):
    user_scores.pop(message.from_user.id, None)
    await bot.send_message(message.chat.id, "Давайте попробуем ещё раз! Начнём заново.")
    await ask_question(message, 0)


# Обработка запроса на контакт с сотрудником
@dp.message_handler(lambda message: message.text == "Связаться с сотрудником")
async def contact_staff(message: types.Message):
    user_id = message.from_user.id

    # Проверяем, есть ли результаты пользователя в словаре
    if user_id not in user_scores:
        await message.answer("Ошибка: ваши результаты не найдены. Пожалуйста, пройдите викторину.")
        return

    scores = user_scores[user_id]
    best_animal = max(scores, key=scores.get)

    # Формируем сообщение для пользователя
    response_message = (
        f"Вы прошли викторину! Ваше тотемное животное — {best_animal}.\n"
        "Чтобы узнать больше о программе опекунства, Вы можете связаться с нашим сотрудником по адресу: "
        "partnershipzoo@culture.mos.ru"
    )

    # Отправляем сообщение пользователю
    await message.answer(response_message)


# Обработка дележа результатами
@dp.message_handler(lambda message: message.text == "Поделиться результатом")
async def share_result(message: types.Message):
    user_id = message.from_user.id
    scores = user_scores[user_id]
    best_animal = max(scores, key=scores.get)

    share_link = "https://t.me/MooZooQuiz?start"
    share_message = f"Я прошел викторину в @ZooQuiz и узнал, что моё тотемное животное — {best_animal}! Присоединяйтесь и узнайте, какое животное подойдёт вам!"

    await bot.send_message(message.chat.id,
                           f"Скопируйте и поделитесь этим сообщением:\n\n{share_message}\n\nСсылка на бота: {share_link}")


# Обработка кнопки "Узнать о программе опеки"
@dp.message_handler(lambda message: message.text == "Узнать о программе опеки")
async def send_care_info(message: types.Message):
    await bot.send_message(message.chat.id,
                           "Программа опеки зоопарка — это отличный способ поддержать животных. Узнайте, как можно стать опекуном и помочь нашим друзьям по ссылке: https://moscowzoo.ru/about/guardianship!")


# Обработка нажатия на кнопку "Оставить отзыв"
@dp.message_handler(lambda message: message.text == "Оставить отзыв")
async def ask_for_feedback(message: types.Message):
    await bot.send_message(message.chat.id, "Пожалуйста, напишите ваш отзыв:")
    await dp.current_state(user=message.from_user.id).set_state("waiting_for_feedback")


# Обработка текста отзыва от пользователя
@dp.message_handler(state="waiting_for_feedback", content_types=types.ContentTypes.TEXT)
async def handle_feedback(message: types.Message):
    user_id = message.from_user.id
    feedback = message.text

    # Формируем сообщение с отзывом
    feedback_message = f"Пользователь {message.from_user.full_name} оставил отзыв:\n\n{feedback}"


    # Отправляем пользователю подтверждение получения отзыва
    await bot.send_message(message.chat.id, "Спасибо за ваш отзыв! Мы обязательно его учтем.",
                           reply_markup=types.ReplyKeyboardRemove())

    # Сбрасываем состояние пользователя
    await dp.current_state(user=user_id).reset_state()

    # Отправляем клавиатуру с кнопками
    keyboard = get_keyboard([
        "Поделиться результатом",
        "Узнать о программе опеки",
        "Связаться с сотрудником",
        "Оставить отзыв",
        "Попробовать ещё раз?",

    ])
    await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard)

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
