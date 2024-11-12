import openai
from transformers import pipeline
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis
import gradio as gr
import json
import sys
# SQLite setup for storing maintenance records
Base = declarative_base()
print(f"step1: setup data base")


class MaintenanceRecord(Base):
    __tablename__ = 'maintenance_records'
    id = Column(Integer, primary_key=True)
    issue_type = Column(String)
    troubleshooting_steps = Column(Text)
    solution = Column(Text)
    logs = Column(Text)

# Initialize database
engine = create_engine('sqlite:///maintenance.db')
#print(f"step2: engine setup ")

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Sample data insertion (populate with real or fictional data)
def populate_sample_data():
    record = MaintenanceRecord(issue_type="Leaking pipe", troubleshooting_steps="Check seals", solution="Replace seal", logs="Pipe was leaking due to worn seal.")
    session.add(record)
    session.commit()

populate_sample_data()

# Using a Hugging Face model for generative responses
generator = pipeline("text-generation", model="gpt2")

# Function to generate responses from the AI model
def generate_response(prompt):
    response = generator(prompt, max_new_tokens=50, num_return_sequences=1)
    return response[0]['generated_text']

# Initialize Redis cache
redis_cache = redis.Redis(host='localhost', port=6379, db=0)

# Function to check cache
def get_cached_response(query):
    #print("get cahche response queri is",query)
    return redis_cache.get(query)

# Function to set cache
def cache_response(query, response):
    #print(f"cache response query is{query} and response is{response}")
    redis_cache.set(query, response, ex=3600)  # Cache for 1 hour

# Retrieve relevant maintenance records based on keywords
def retrieve_relevant_records(query):
   # print(f"retrieve relevant records is {query}")
    results = session.query(MaintenanceRecord).filter(MaintenanceRecord.issue_type.ilike(f"%{query}%")).all()
    if results:
        return " ".join([f"Issue: {r.issue_type}, Solution: {r.solution}" for r in results])
    return "No relevant records found."

# Combine retrieval with generation for contextual response
def rag_response(query):
    cached_response = get_cached_response(query)
    if cached_response:
        return cached_response.decode("utf-8")
    
    relevant_records = retrieve_relevant_records(query)
    prompt = f"{query}\n{relevant_records}\nSuggested Solution:"
    response = generate_response(prompt)
    
    cache_response(query, response)
    return response
# Define Gradio interface
def maintenance_assistant(query):
  #  print(f"maintainace query")
    return rag_response(query)
def fallback_solution(query):
    if 'leaking pipe' in query.lower():
        return "Here are some general steps you can follow to fix a leaking pipe: 1) Turn off the water supply, 2) Identify the leak, 3) Use appropriate sealing methods or call a plumber."
    else:
        return "Sorry, I couldn't find a relevant solution for your issue."




# Launch Gradio app
iface = gr.Interface(fn=maintenance_assistant, inputs="text", outputs="text", title="Maintenance Support Assistant")
iface.launch()
