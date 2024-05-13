from flask import Flask, request, jsonify, g
from PyPDF2 import PdfReader
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from flask_cors import CORS
import os 
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv



app = Flask(__name__)
CORS(app)

load_dotenv()
os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


uri = "mongodb+srv://sid:siddhanth@cluster0.vxzv5gj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# Create a new client and connect to the server
client = MongoClient(uri)

db = client['Cluster0']  
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
    
QNA_collection = db['QNA_data']

global vectors , question_type, difficulty_level, subject 



@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    global vectors , question_type, difficulty_level, subject 
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No PDF file uploaded'}), 400
    
    question_type = request.form.get('question_type')
    difficulty_level = request.form.get('difficulty_level')
    subject= request.form.get('subject')
    # topic_name = request.form.get('topic_name')
    pdf_file = request.files['pdf_file']
    vectors = extract_text_from_pdf(pdf_file)
    
   

 
    return jsonify({'message': 'PDF uploaded successfully'})

@app.route('/api/generate_qna', methods=['GET'])
def generate_qa():
    global vectors , question_type, difficulty_level, subject 
    if vectors is None:
        return jsonify({'error': 'Vectors not found'}), 400
    
    
    if difficulty_level == 'easy':
        level_prompt = "easy : The question of type fill in blanks should be conceptual" 
    elif difficulty_level == 'medium':
        level_prompt = "medium : The question of type fill in blanks should be basic and easy but application based according to the given context" 
    elif difficulty_level == 'hard':
        level_prompt = "hard : The question of type fill in blanks should be a difficult application based question according to the given context" 
    
    
    prompts = {
      'fill_in_the_blank': f"Read the following passage: {' '.join(vectors)}.  questions of the type Generate fill-in-the-blank with at least 3 options for each blank, incorporating the difficulty level {level_prompt}.The format of your response should be \n Question(use '____' for indicating the blanks): \n Answer: ",
      'true_or_false': f"Read the following passage: {' '.join(vectors)}. Generate True/False questions based on the passage, incorporating the difficulty level {level_prompt}.The format of the response given by you should be \n Question with a statement in last write whether the statment is true or false: \n Answer:",
      'mcq': f"Read the following passage: {' '.join(vectors)}. Generate multiple choice questions with 4 options for each question, incorporating the difficulty level {level_prompt}.The format of the response should be \n Question: \n options: a)    b)    c)    d)\n answer (with the option number):"
  }
    print("i have reached here 5")
    if question_type == 'fill_in_the_blank':
        type_prompt = prompts['fill_in_the_blanks']
    elif question_type == 'true_or_false':
        type_prompt = prompts['true_or_false']
    else:
        type_prompt = prompts['mcq']
    
    prompt_template =  f"generate 5 questions based on the following prompts: {type_prompt}"
    
    
    if question_type not in prompts:
       return jsonify({'error': 'Invalid question type'}), 400
   
     
    generation_config = {
  "temperature": 0.5,
  "top_p": 0.95,
  "top_k": 0,
  "max_output_tokens": 8192,
}
    
    model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",generation_config=generation_config)
    # prompt_text = prompt_template.render(variables={'type_prompt': type_prompt})
    response = model.generate_content(prompt_template)
    response1 = f'{response}'
    print(response1)
    
    
    questions_answers = []
    if question_type == 'fill_in_the_blank':
          # Extract question and answer choices from the generated text
          question, *answer_choices = response1.split(' [BLANK]')
          questions_answers.append({
              'question': question.strip(),
              'answer_choices': answer_choices,
              'questionType': question_type
          })
    else:
          # Extract question and answer (True/False) from the generated text
          question_answer = response1.split('?')
          questions_answers.append({
              'question': question_answer[0].strip(),
              'answer': question_answer[1].strip() if len(question_answer) > 1 else None,
              'questionType': question_type
          })

    
    qna_data = {
         'question_type' : question_type,
         'difficulty_level' : difficulty_level,
         'subject': subject,
         'questions_answers': questions_answers
    }
    try:
        QNA_collection.insert_one(qna_data)
    except Exception as e:
        print(e)
        
    
    return jsonify({'questions_answers_ntype': questions_answers})

def extract_text_from_pdf(pdf_file):
    raw_text = ''
    # print("i have reached here 1")
    pdf_reader = PdfReader(pdf_file)
    # print("i have reached here 2")
    for page in pdf_reader.pages:
        # print("i have reached here 3")
        raw_text += page.extract_text()
        # print("i have reached here 4")
        
    return raw_text


if __name__ == '__main__':
    app.run(debug=True)