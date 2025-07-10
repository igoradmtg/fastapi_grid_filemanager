import os
import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil # Импортируем модуль shutil для перемещения файлов
# Инструкция для установки
# pip install fastapi uvicorn gradio
# Убедитесь, что папки для сохранения и отправленных файлов существуют
SAVE_DIR = "saved_files"
SENDED_DIR = "sended_files" # Новая папка для отправленных файлов

os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(SENDED_DIR, exist_ok=True) # Создаем папку для отправленных файлов

# --- Функции для работы с файлами ---

def save_text_to_file(content, filename):
    file_path = os.path.join(SAVE_DIR, filename)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Текст успешно сохранён в файл: {filename}"
    except Exception as e:
        return f"❌ Ошибка при сохранении файла: {str(e)}"

def list_filenames():
    """Возвращает список только имен файлов для Gradio Radio из SAVE_DIR."""
    try:
        files = [f for f in os.listdir(SAVE_DIR) if os.path.isfile(os.path.join(SAVE_DIR, f))]
        return files
    except Exception as e:
        return [] # Возвращаем пустой список в случае ошибки

def delete_file(filename):
    file_path = os.path.join(SAVE_DIR, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return f"🗑️ Файл '{filename}' успешно удален."
        except Exception as e:
            return f"❌ Ошибка при удалении файла '{filename}': {str(e)}"
    else:
        return f"⚠️ Файл '{filename}' не найден."

def read_file_content(filename):
    file_path = os.path.join(SAVE_DIR, filename)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            return f"❌ Ошибка при чтении файла '{filename}': {str(e)}"
    else:
        return f"⚠️ Файл '{filename}' не найден."

# --- Создаём FastAPI-приложение ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/get-file/{filename}")
async def get_file_fastapi(filename: str):
    file_path = os.path.join(SAVE_DIR, filename)
    
    if not os.path.exists(file_path):
        return JSONResponse(content={"error": "Файл не найден"}, status_code=404)
    
    try:
        response = FileResponse(file_path, filename=filename)
        # После успешной отправки файла, перемещаем его в SENDED_DIR
        @response.background
        async def move_file_after_send():
            destination_path = os.path.join(SENDED_DIR, filename)
            try:
                shutil.move(file_path, destination_path)
                print(f"Файл '{filename}' успешно перемещен в '{SENDED_DIR}' после скачивания.")
            except Exception as e:
                print(f"Ошибка при перемещении файла '{filename}' в '{SENDED_DIR}': {str(e)}")
        
        return response
    except Exception as e:
        return JSONResponse(content={"error": f"Ошибка при получении файла: {str(e)}"}, status_code=500)


@app.post("/upload-file-from-body")
async def upload_file_from_body(request: Request):
    try:
        data = await request.json()
        content = data.get("body")
        filename = data.get("filename")

        if not content or not filename:
            return JSONResponse(content={"error": "Отсутствуют 'body' или 'filename' в запросе."}, status_code=400)

        file_path = os.path.join(SAVE_DIR, filename)
        with open(file_path, "w", encoding="utf-            8") as f:
            f.write(content)
        return JSONResponse(content={"message": f"Файл '{filename}' успешно загружен."}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": f"Ошибка при загрузке файла: {str(e)}"}, status_code=500)

@app.get("/get-first-file/")
async def get_first_file():
    try:
        files = [f for f in os.listdir(SAVE_DIR) if os.path.isfile(os.path.join(SAVE_DIR, f))]
        if not files:
            return JSONResponse(content={"error": "В каталоге 'saved_files' нет файлов."}, status_code=404)
        
        first_filename = files[0]
        file_path = os.path.join(SAVE_DIR, first_filename)
        
        try:
            response = FileResponse(file_path, filename=first_filename)
            # После успешной отправки файла, перемещаем его в SENDED_DIR
            @response.background
            async def move_first_file_after_send():
                destination_path = os.path.join(SENDED_DIR, first_filename)
                try:
                    shutil.move(file_path, destination_path)
                    print(f"Файл '{first_filename}' успешно перемещен в '{SENDED_DIR}' после скачивания.")
                except Exception as e:
                    print(f"Ошибка при перемещении файла '{first_filename}' в '{SENDED_DIR}': {str(e)}")
            
            return response
        except Exception as e:
            return JSONResponse(content={"error": f"Ошибка при получении первого файла: {str(e)}"}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"error": f"Ошибка при получении первого файла: {str(e)}"}, status_code=500)

# --- Gradio-интерфейс ---

text_save_interface = gr.Interface(
    fn=save_text_to_file,
    inputs=[
        gr.Textbox(label="Текст для сохранения", lines=5),
        gr.Textbox(label="Имя файла", placeholder="Введите имя файла с расширением, например: example.txt")
    ],
    outputs=gr.Textbox(label="Результат сохранения"),
    title="Сохранение текста в файл",
    description="Введите текст и имя файла, затем нажмите 'Submit' для сохранения",
    examples=[["Пример текста", "example.txt"]]
)

with gr.Blocks() as file_manager_interface:
    gr.Markdown("### Управление загруженными файлами")

    # Используем gr.Radio для выбора файла из списка
    # Важно: list_filenames() должна возвращать список строк
    file_selector = gr.Radio(
        list_filenames(), # Опции будут загружены при инициализации
        label="Выберите файл:",
        interactive=True,
        scale=1
    )
    
    refresh_button = gr.Button("Обновить список файлов", scale=0) # Меньший размер кнопки

    # Поле для ввода имени файла для операций
    selected_filename_input = gr.Textbox(
        label="Имя выбранного файла", 
        placeholder="Имя файла появится здесь после выбора", 
        interactive=True # Сделаем интерактивным, чтобы его можно было изменить вручную
    )

    with gr.Row():
        delete_button = gr.Button("Удалить файл")
        view_button = gr.Button("Посмотреть содержимое")

    operation_result_output = gr.Textbox(label="Результат операции", interactive=False, lines=5)

    # Привязываем изменение выбора в gr.Radio к полю selected_filename_input
    file_selector.change(
        lambda x: x, # Простая функция, которая возвращает то, что получила
        inputs=file_selector,
        outputs=selected_filename_input
    )

    # Привязываем refresh_button к обновлению списка файлов в gr.Radio
    refresh_button.click(
        lambda: gr.update(choices=list_filenames(), value=None), # Обновляем опции и сбрасываем выбор
        inputs=None,
        outputs=file_selector
    ).then(
        lambda: "", # Очищаем поле выбранного файла после обновления списка
        inputs=None,
        outputs=selected_filename_input
    )

    # Логика кнопок Удалить и Посмотреть содержимое
    # После удаления или просмотра обновляем список файлов и выбранный файл
    delete_button.click(
        delete_file,
        inputs=selected_filename_input,
        outputs=operation_result_output
    ).then(
        lambda: gr.update(choices=list_filenames(), value=None), # Обновляем опции Radio
        inputs=None,
        outputs=file_selector
    ).then(
        lambda: "", # Очищаем поле выбранного файла
        inputs=None,
        outputs=selected_filename_input
    )

    view_button.click(read_file_content, inputs=selected_filename_input, outputs=operation_result_output)

    # Инициализация списка файлов при загрузке страницы
    file_manager_interface.load(
        lambda: gr.update(choices=list_filenames()),
        inputs=None,
        outputs=file_selector
    )


full_interface = gr.TabbedInterface(
    [text_save_interface, file_manager_interface],
    ["Сохранить текст", "Управление файлами"]
)

app = gr.mount_gradio_app(app, full_interface, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
