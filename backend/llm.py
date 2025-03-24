import os
from typing import Dict, List, Any, Optional
from langchain_community.chat_models import ChatLiteLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import SystemMessage, HumanMessage, AIMessage

# Set up LLM
api_base = os.getenv("LLM_API_BASE", "http://localhost:11434")
model_name = os.getenv("LLM_MODEL_NAME", "ollama/gemma3:12b")

llm = ChatLiteLLM(
    api_base=api_base,
    model_name=model_name,
)

async def generate_event_metadata(content: str) -> Dict[str, str]:
    """
    Generate event metadata (topic and description) using LLM
    
    Args:
        content: Event content (notes and transcription)
        
    Returns:
        Dictionary with topic and description
    """
    # Modified to use a single human message instead of system+human message
    system_instruction = """You are an AI assistant that helps create concise and accurate metadata for events. 
    Based on the provided notes and transcription, generate a short professional title and a brief description for the event.
    The title should be no more than 5-7 words. The description should be 1-2 sentences, maximum 25 words.
    Both should capture the essence of the event professionally and be suitable for a LinkedIn post."""
    
    human_template = """{system_instruction}

    Here are the notes and transcription from an event:
    {content}
    
    Generate a professional title and a brief description for this event. Respond in JSON format with 'topic' and 'description' keys."""
    
    prompt = human_template.format(
        content=content,
        system_instruction=system_instruction
    )
    
    # Get response from LLM with combined prompt using ainvoke
    messages = [
        HumanMessage(content=prompt)
    ]
    
    response = await llm.ainvoke(messages)
    
    # Try to parse JSON from response
    import json
    try:
        # First, try to find JSON in the response if it's not pure JSON
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response.content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # If no code block, try to find anything that looks like JSON
            json_match = re.search(r'({.*})', response.content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.content
                
        metadata = json.loads(json_str)
        
        # Ensure we have the expected keys
        if 'topic' not in metadata or 'description' not in metadata:
            # Extract from plain text if JSON is missing keys
            if 'topic' not in metadata:
                topic_match = re.search(r'Title:?\s*(.*?)(?:\n|$)', response.content)
                metadata['topic'] = topic_match.group(1) if topic_match else "Untitled Event"
            
            if 'description' not in metadata:
                desc_match = re.search(r'Description:?\s*(.*?)(?:\n|$)', response.content)
                metadata['description'] = desc_match.group(1) if desc_match else "No description provided"
        
        return metadata
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        print(f"Response was: {response.content}")
        
        # Fallback to simple extraction
        import re
        topic_match = re.search(r'(?:Title|Topic):?\s*(.*?)(?:\n|$)', response.content)
        desc_match = re.search(r'(?:Description|Summary):?\s*(.*?)(?:\n|$)', response.content)
        
        return {
            "topic": topic_match.group(1) if topic_match else "Untitled Event",
            "description": desc_match.group(1) if desc_match else "No description provided"
        }

async def generate_post(metadata: Dict[str, str], notes: str, transcription: str) -> str:
    """
    Generate a LinkedIn post based on event metadata, notes, and transcription
    
    Args:
        metadata: Event metadata (topic, description, date)
        notes: User notes
        transcription: Audio transcription
        
    Returns:
        Generated LinkedIn post content
    """
    # Modified to use a single human message with system instructions included
    system_template = """You are a professional LinkedIn content creator. 
    Your task is to create an engaging, professional LinkedIn post based on event information.
    The post should be concise (150-200 words), engaging, and formatted appropriately for LinkedIn.
    Include relevant hashtags at the end of the post.
    Focus on the key insights and value from the event."""
    
    human_template = """{system_template}
    
    Please create a LinkedIn post about this event:
    
    Topic: {topic}
    Description: {description}
    Date: {date}
    
    Additional information:
    Notes: {notes}
    Transcription: {transcription}
    
    Create a professional LinkedIn post that would be appropriate to share with my network."""
    
    # Prepare formatted input
    prompt = human_template.format(
        system_template=system_template,
        topic=metadata.get("topic", ""),
        description=metadata.get("description", ""),
        date=metadata.get("date", ""),
        notes=notes,
        transcription=transcription
    )
    
    # Get response from LLM with combined prompt using ainvoke
    messages = [
        HumanMessage(content=prompt)
    ]
    
    response = await llm.ainvoke(messages)
    return response.content

async def edit_post(current_post: str, metadata: Dict[str, str], messages: List[Dict[str, str]]) -> str:
    """
    Edit a LinkedIn post based on user feedback
    
    Args:
        current_post: Current version of the post
        metadata: Event metadata
        messages: Chat messages with user feedback
        
    Returns:
        Edited LinkedIn post content
    """
    system_template = """You are a professional LinkedIn content editor.
    Your task is to edit a LinkedIn post based on user feedback.
    Maintain the professional tone and keep the post concise and engaging.
    Apply the specific edits requested by the user."""
    
    # Format chat history from messages
    chat_history = []
    for msg in messages:
        if hasattr(msg, 'role') and hasattr(msg, 'content'):
            # It's a Pydantic model
            if msg.role == "user":
                chat_history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                chat_history.append(AIMessage(content=msg.content))
        elif isinstance(msg, dict) and "role" in msg and "content" in msg:
            # It's a dictionary
            if msg["role"] == "user":
                chat_history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                chat_history.append(AIMessage(content=msg["content"]))
    
    # Add context about the current post and event metadata
    context = f"""
    {system_template}
    
    Event Topic: {metadata.get('topic', '')}
    Event Description: {metadata.get('description', '')}
    Event Date: {metadata.get('date', '')}
    
    Current LinkedIn Post:
    {current_post}
    
    Please edit the LinkedIn post according to my feedback.
    """
    
    # Add context as the first user message if there are no messages yet
    if not chat_history:
        chat_history.append(HumanMessage(content=context))
    else:
        # Insert context before the first message
        chat_history.insert(0, HumanMessage(content=context))
    
    # Use only user messages, remove system message approach
    # Get response from LLM using ainvoke
    response = await llm.ainvoke(chat_history)
    return response.content