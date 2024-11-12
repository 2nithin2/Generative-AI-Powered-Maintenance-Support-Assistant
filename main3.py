import openai 
from transformers import pipeline
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis
import gradio as gr
import sys

# SQLite setup for storing maintenance records
Base = declarative_base()

class MaintenanceRecord(Base):
    __tablename__ = 'maintenance_records'
    id = Column(Integer, primary_key=True)
    issue_type = Column(String)
    troubleshooting_steps = Column(Text)
    solution = Column(Text)
    logs = Column(Text)

# Initialize database
def init_db():
    engine = create_engine('sqlite:///maintenance.db')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

session = init_db()

# Sample data insertion (populate with real or fictional data)
def populate_sample_data():
    record = MaintenanceRecord(
        issue_type="Leaking pipe",
        troubleshooting_steps="Check seals",
        solution="Replace seal",
        logs="Pipe was leaking due to worn seal."
    )
    session.add(record)
    session.commit()

populate_sample_data()

# Initialize Redis cache with error handling
def init_redis():
    try:
        return redis.Redis(host='localhost', port=6379, db=0)
    except redis.exceptions.ConnectionError:
        print("Redis connection error. Ensure Redis is running.")
        sys.exit(1)

redis_cache = init_redis()

# Using a Hugging Face model for generative responses
generator = pipeline("text-generation", model="gpt2")

# Function to generate responses from the AI model
def generate_response(prompt):
    response = generator(prompt, max_new_tokens=50, num_return_sequences=1)
    return response[0]['generated_text']

# Redis cache functions
def get_cached_response(query):
    return redis_cache.get(query)

def cache_response(query, response):
    redis_cache.set(query, response, ex=3600)  # Cache for 1 hour

# Solution for leaking pipe issues
def pipe_leak_solution():
    return ("It seems like you're dealing with a leaking pipe. Here are some steps you can follow:\n"
            "1) Turn off the water supply to prevent further leakage.\n"
            "2) Inspect the pipe to locate the leak.\n"
            "3) Use pipe tape, a pipe clamp, or epoxy putty to seal the leak temporarily.\n"
            "4) Contact a plumber if the leak persists or if you're unable to fix it on your own.")

# Solution for internet connectivity issues
def internet_connectivity_solution():
    return ("It seems like you're experiencing internet connectivity issues. Here are some steps you can try:\n"
            "1) Check if the Wi-Fi router is powered on and connected properly.\n"
            "2) Restart the router and modem by unplugging them for 10 seconds, then plugging them back in.\n"
            "3) Ensure that your device is connected to the correct network.\n"
            "4) If the issue persists, contact your Internet Service Provider (ISP) to check for outages.")

# Solution for power outage issues
def power_outage_solution():
    return ("It seems like you're dealing with a power outage. Here are some steps to follow:\n"
            "1) Check if the power is out in your entire building or just your unit.\n"
            "2) Look at your circuit breaker to see if any switches are tripped.\n"
            "3) If a breaker is tripped, reset it by turning it off and then back on.\n"
            "4) If power doesn’t return, contact your local electricity provider for assistance.")

def find_keys_containing_value(dictionary, value):
        matching_keys = [key for key, values in dictionary.items() if value in values]
        return matching_keys
def check_issues(query):
    # Example dictionary with lists of issues as values
    issues = {
        "plumb": ["pipe", "leak", "clog"],
        "internet": ["connectivity", "slow speed", "no signal"],
        "power": ["outage", "fluctuation", "overload"]
    }
    # Function to find keys containing the specified value
    # Usage
    keys_with_query = find_keys_containing_value(issues, query)
    return keys_with_query
   

    #print(f"The value '{query}' is found in the following key(s): {keys_with_query}")

# Check for known issues and return predefined responses
def query_issue_type(query):
    # if 'pipe leak' in query.lower() or 'leaking pipe' in query.lower():
    #     return pipe_leak_solution()
    # elif 'internet connectivity' in query.lower() or 'no internet' in query.lower():
    #     return internet_connectivity_solution()
    # elif 'power outage' in query.lower() or 'no power' in query.lower():
    #     return power_outage_solution()
    # return None  # Return None if no match is found
    pipe_terms=["pipe","leakage","leaking","water","clogg"]
    internet_terms=["connectivity","internet","wifi"]
    power_terms=["power","outage","electricity","no power"]
    query=(query.lower()).split()
    issue=check_issues(query)
    issue_handlers = {
    "plumb": pipe_leak_solution,
    "internet": internet_connectivity_solution,
    "power": power_outage_solution
}
    print(issue,type(issue),"\n done executing")

    sys.exit()
    action = issue_handlers.get(issue, lambda: "Unknown issue. Please provide more details.")
    if action:
        return action()
    else:
        retrieve_relevant_records(("").join(query))
    
# Retrieve relevant maintenance records from the database
def retrieve_relevant_records(query):
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

# Primary function to handle maintenance queries
def maintenance_assistant(query):
    predefined_response = query_issue_type(query)
    if predefined_response:
        return predefined_response
    return rag_response(query)

# Define Gradio interface
iface = gr.Interface(fn=maintenance_assistant, inputs="text", outputs="text", title="Maintenance Support Assistant")
iface.launch()