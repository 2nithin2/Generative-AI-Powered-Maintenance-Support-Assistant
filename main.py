# Import necessary libraries
import openai  # OpenAI library, for potential use of OpenAI models (not actually used in this script)
from transformers import pipeline  # Hugging Face library for NLP models (e.g., text generation)
from sqlalchemy import create_engine, Column, Integer, String, Text  # SQLAlchemy tools for setting up a database
from sqlalchemy.ext.declarative import declarative_base  # Base class for ORM mappings
from sqlalchemy.orm import sessionmaker  # Tool to create session objects for database transactions
import redis  # Library for Redis, used here as a caching mechanism
import gradio as gr  # Gradio library for creating a web-based interface
import json  # JSON library for data handling
import sys  # System-specific parameters and functions

# SQLAlchemy base class for ORM (Object Relational Mapping)
Base = declarative_base()
print(f"step1: setup data base")


class MaintenanceRecord(Base):
    """
    A class representing a maintenance record in the database.

    Attributes:
    id (int): The unique identifier for the maintenance record.
    issue_type (str): The type of issue faced (e.g., "Leaking pipe").
    troubleshooting_steps (str): The steps taken to troubleshoot the issue.
    solution (str): The solution applied to fix the issue.
    logs (str): Additional logs that provide context about the issue and solution.

    Methods:
    None
    """
    __tablename__ = 'maintenance_records'
    id = Column(Integer, primary_key=True)  # Primary key for each record
    issue_type = Column(String)  # Type of issue
    troubleshooting_steps = Column(Text)  # Steps taken to troubleshoot
    solution = Column(Text)  # Solution to the issue
    logs = Column(Text)  # Logs for additional context


# Initialize SQLite database and create the table if it doesn't exist
engine = create_engine('sqlite:///maintenance.db')
#print(f"step2: engine setup ")

Base.metadata.create_all(engine)  # Create the table
Session = sessionmaker(bind=engine)
session = Session()  # Start a new session for database transactions


def populate_sample_data():
    """
    Function to populate the database with a sample maintenance record.

    This function inserts a sample maintenance record related to a leaking pipe
    with troubleshooting steps, solution, and logs into the database.

    Returns:
    None
    """
    record = MaintenanceRecord(
        issue_type="Leaking pipe", 
        troubleshooting_steps="Check seals", 
        solution="Replace seal", 
        logs="Pipe was leaking due to worn seal."
    )
    session.add(record)  # Add record to session
    session.commit()  # Commit to save changes


populate_sample_data()  # Populate the database with sample data


def generate_response(prompt):
    """
    Generates a text response using a Hugging Face transformer model.

    Args:
    prompt (str): The input text or query to generate a response for.

    Returns:
    str: The generated response based on the input prompt.
    """
    response = generator(prompt, max_new_tokens=50, num_return_sequences=1)
    return response[0]['generated_text']


# Initialize Redis cache
redis_cache = redis.Redis(host='localhost', port=6379, db=0)


def get_cached_response(query):
    """
    Retrieves a cached response from the Redis database.

    Args:
    query (str): The query for which to retrieve the cached response.

    Returns:
    str: The cached response, if found. Otherwise, None.
    """
    return redis_cache.get(query)


def cache_response(query, response):
    """
    Caches a response in Redis with a 1-hour expiry time.

    Args:
    query (str): The query to associate with the response.
    response (str): The generated response to cache.

    Returns:
    None
    """
    redis_cache.set(query, response, ex=3600)  # Cache for 1 hour


def retrieve_relevant_records(query):
    """
    Retrieves relevant maintenance records from the database based on the query.

    Args:
    query (str): The query to search for in the maintenance records.

    Returns:
    str: A string summarizing the relevant records or a message if no records are found.
    """
    results = session.query(MaintenanceRecord).filter(MaintenanceRecord.issue_type.ilike(f"%{query}%")).all()
    if results:
        return " ".join([f"Issue: {r.issue_type}, Solution: {r.solution}" for r in results])
    return "No relevant records found."


def rag_response(query):
    """
    Combines retrieval of relevant records and generation of an AI-based response.

    This function checks if a cached response exists. If not, it retrieves relevant
    maintenance records from the database, generates an AI response, and caches the result.

    Args:
    query (str): The user's query for which a response is required.

    Returns:
    str: The generated response, either from cache or generated dynamically.
    """
    cached_response = get_cached_response(query)
    if cached_response:
        return cached_response.decode("utf-8")
    
    relevant_records = retrieve_relevant_records(query)
    prompt = f"{query}\n{relevant_records}\nSuggested Solution:"
    response = generate_response(prompt)
    
    cache_response(query, response)
    return response


def maintenance_assistant(query):
    """
    Handles the main logic for the maintenance assistant.

    This function is called by Gradio's interface to generate a response
    to the user's query by leveraging RAG (Retrieve and Generate) logic.

    Args:
    query (str): The user's query for the assistant.

    Returns:
    str: The generated response for the user.
    """
    return rag_response(query)


def fallback_solution(query):
    """
    Provides a fallback solution if no relevant records are found.

    This function is used to provide a basic solution in case no database
    entries match the user's query. For example, if the query contains
    'leaking pipe', a default solution will be returned.

    Args:
    query (str): The user's query.

    Returns:
    str: A fallback solution or message indicating no solution could be found.
    """
    if 'leaking pipe' in query.lower():
        return "Here are some general steps you can follow to fix a leaking pipe: 1) Turn off the water supply, 2) Identify the leak, 3) Use appropriate sealing methods or call a plumber."
    else:
        return "Sorry, I couldn't find a relevant solution for your issue."


# Gradio Interface Setup: Launches a web interface for the maintenance assistant
iface = gr.Interface(
    fn=maintenance_assistant,  # The main function to call
    inputs="text",  # Text input for the query
    outputs="text",  # Text output for the response
    title="Maintenance Support Assistant"  # Title of the web interface
)
iface.launch()
