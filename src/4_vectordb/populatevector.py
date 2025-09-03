import argparse, sqlite3, uuid, json, os, sys
import numpy as np
from hashlib import blake2b
from typing import Iterable
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def embed_openai(text: str):
    """
    Embeds the texts into a float32 vector with OpenAI's embedding
    """
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def embed(text: str):
    """
    Deterministically hash a string into a float32 vector, and also populate the l2norm for faster cosine similarity 
    """
    vec  = np.asarray(embed_openai(text), dtype="float32")  
    norm = np.linalg.norm(vec)

    return vec, norm


DDL = """
CREATE TABLE IF NOT EXISTS vectors (
    id       TEXT PRIMARY KEY,
    dim      INTEGER NOT NULL,
    data     BLOB    NOT NULL,
    l2_norm  REAL    NOT NULL,
    metadata JSON
);
CREATE INDEX IF NOT EXISTS idx_vectors_norm ON vectors (l2_norm);
"""

def insert_batch(cur, rows):
    cur.executemany(
        "INSERT INTO vectors (id, dim, data, l2_norm, metadata) VALUES (?,?,?,?,?)",
        rows,
    )

def main():
    con = sqlite3.connect("./localvector.db")
    con.executescript(DDL)
    cur = con.cursor()

    text_sample = """
        Buah Batu Regency, F5 no 3 
        Bandung, Indonesia

        Rayza Mahendra G H



        +62 8966 6634 343
        rayzamgh@gmail.com
        https://www.rayzamahendra.xyz
        github.com/rayzamgh

        WORK EXPERIENCE

        Machine Learning Engineer				Telkomsel	           	           July 2023 - Present
        Spearheaded the implementation of inhouse LLMOps Platform and multiple GenAI use cases to enhance business operations, serving as the technical lead:
        Probing Machine: Developed a system for analysing offer prices between Telkomsel and its competitors.
        Root Cause Analysis Chatbot: Implemented a chatbot that analyzes business questions related to financial performance.
        Smart Data Catalog: Established a batch system to manage and populate metadata for data tables, including descriptions and classification levels.
        Summarizer System: Created a multi-level problem summarizer for all Telkomsel branches, organizing issues from the branch level up to the national level.
        Many more AI projects I cannot officially list in my CV, we can talk about this directly
        In-house MLops & LLMops Platform: Took part in developing and maintaining an in-house MLops platform. This platform is responsible for managing the full lifecycles of ML Models used across Telkomsel. Key technologies involved include Elyra, Kubernetes, and FastAPI.
        KTP OCR Development: Implemented an OCR system for extracting information from Indonesian ID cards (KTP). Focused on improving the system's resilience to handle tilted, skewed, and rotated data, enhancing process robustness. The system was developed using PaddleOCR, Python, and TensorFlow.
        Tech stack used : Airflow, AWS Cloud, OpenAI GPT, Gemini, Guardrail, Dify LLMops, Langchain, and Kubernetes
        Managed vendor teams, overseeing the development of these use cases and ensuring adherence to code conduct and delivery timelines.
        Data Scientist					JobKred	           	           August 2021 - July 2023
        Developed and researched machine learning solutions to accommodate business processes. Worked with various language models such as GPT-2 and BERT
        Developed and maintained a web crawler pipeline to scrape job ads and identify trending skills in the market.
        Developed and maintained two separate python and javascript testing CICD with Pytest, Playwright, Artillery, and Github Action. 
        Tech stack used: huggingface, Python, PyTorch, Airflow, Django, scrapy, docker, Kubernetes, GCP, BigQuery, Google PubSub.

        Fullstack Software Engineer Part-Time   		JobKred	           	           August 2021 - May 2022
        Developed and maintained internal Data Engineering applications concerned with data annotation and interpretation.
        Developed and maintained web crawler pipeline to scrape job ads and identify trending skills in the market.
        Tech stack used: Airflow, Django, scrapy, docker, Kubernetes, GCP, BigQuery, Google PubSub.
        Lead Chatbot Developer Part-Time    		        	Chatbiz	           		      February 2021 - June 2021
        Developed and maintained WhatsApp Chatbot.
        Developed with the serverless framework, Node.js, AWS Lambda, AWS step-functions and DynamoDB
        Uses Wit.ai, Google Dialogflow, and Rasa NLP Chatbot framework SDK development for intent classification.
        Automated wit.ai utterances, and intent training with Golang.

        Backend Developer Part-Time		          	Xtremax	           February 2020 - November 2020
        Developed and maintained an established ASP.NET MVC Website.
        Developed event-based module for Sitecore Content Editor.
        Sitecore CMS project developments and maintenance.
        Tech stack used: Sitecore, ASP.NET, C#, Docker, Bitbucket, MSSQL.

        Backend Engineer Intern 				 Roketin			May 2019 - July 2019
        Developed server-side web API and handled NoSQL state exchange for an insurance company. 
        Refactored transaction microservice to a new REST API structure resulting in a 20% increase in request handling speed.
        Tech stack used: Docker, Golang, GitLab, MongoDB, Go-Chi.

        INDUSTRY PUBLICATIONS & WHITE PAPERS
        Global Telecom Awards 2024 - Automation Initiative of the Year - Finalist
        AI-Powered Competitor Insight Engine (ACE) Probing Machine
        IDC Future Enterprise Awards 2025 - Best in Artificial and Generative Intelligence
        Galilei Generative AI and LLM End-to-End Integrated System
        EDUCATION
        Master’s degree in Computer Science		 Institut Teknologi Bandung          August 2021 - September 2022
        GPA 3.81/4.00 (cum laude)
        Fast-Track Program (Bachelor - Master Degree) in 5 Years.
        Relevant coursework: Advanced Natural Language Processing, Pattern Recognition, etc.
        Also worked as Knowledge Representation and Pattern Recognition course assistant
        Master’s Thesis: Few-shot Learning in Indonesian Language Text Classification.
        Bachelor’s degree in Informatics 		 Institut Teknologi Bandung 		  July 2017 - July 2021
        GPA 3.65/4.00 (cum laude).
        Relevant coursework: Machine Learning, Deep Learning, Object-Oriented Programming, Cloud Computing, etc.
        Bachelor’s Thesis: Development of Citation Intent Classification and Citation Sentiment Classification Model on COVID-19 Dataset.

        TECHNICAL EXPERIENCE

        PROJECTS
        Bank Indonesia - Public Perception AI Platform(2025)
        Acted as a tech-lead in the development of Bank Indonesia’s AI Platform to monitor and gather feedback from public news sources. We used Agentic AI to digest daily news sources into multiple categories and multiple intents and sentiments to gauge public’s responses on new BI policies.

        Few-shot learning in the Indonesian Language (2022)
        My Master’s Thesis in Natural Language Processing presents a new alternative to Indonesian text classification using very minimal data while achieving competitive results to all-shot approach. Benchmarked on IndoNLU dataset, Uses GPT-Neo, IndoGPT, XGLM, XLM-R, Huggingface, and Pytorch for research.

        PA-GPT Personal Assistant (2022)
        Developed an innovative web-based AI companion utilizing GPT and Langchain, featuring diverse functionalities including internet search, Wolfram-Calculator for complex math, Arxiv for academic paper summaries, Python coding capabilities, Wikipedia information retrieval, and an experimental Gmail management tool. Notably, the project includes 'Rayza-QA', a unique function accessing a vector text-embedded Google Docs autobiography, designed to provide interactive insights about me for potential interviewers.
        More details can be found below : 
        https://portfolio-web-249407.web.app/chatbot
        https://www.linkedin.com/pulse/yet-another-ai-assistant-rayza-mahendra%3FtrackingId=gCyL68UIS3mc557Hu1qF8Q%253D%253D/?trackingId=gCyL68UIS3mc557Hu1qF8Q%3D%3D

        Citation Intent & Sentiment Analysis (2021)
        Final year project of my bachelor’s thesis, the system uses the CORD-19 dataset to map scientific journals citation into knowledge graphs. Classifier uses SciBERT, Word2vec and XLnet. 

        Argus - Social Network Analysis Tools (2019)
        WebApp social network analysis software to map relations on Twitter sentimentality demographics commissioned by the Social Relations Ministry in KM ITB. 
        Techstack used: Laravel, MySQL, D3.js.

        Therwell - Well Property Prediction Tools (2019)
        Desktop app to measure well properties at various depths implements a pre-established calculation
        Techstack used : Tkinter, Python, Pandas.


        SKILLS
        Comfortable in Python, Golang, C#, Javascript, C++, and Java. 
        Deep Learning understanding and somewhat familiar with Keras and Tensorflow.
        Have basic knowledge and know-how in using NLTK, and Spacy for Natural Language Processing tasks.
        Familiar with Git, Docker, AWS, and similar cloud computing engines.
        Familiar with designing REST API with frameworks such as Django, Express JS, Node, Go.
        Converse in business level verbal and written English. 

        LEADERSHIP EXPERIENCE AND ORGANIZATION
        HMIF - Head of Kinship Division (2020).
        Genshiken ITB - Vice Head of Kinship Division (2019).
        Genshiken ITB - Vice Head of Musical Division (2018).

        ACHIEVEMENTS
        HackSense, Hackathon by Codersense 2020, 1st Prize Winner.
        Global Telecom (Glotel) Awards 2024, Paper Finalist on AI & Automation, Competitor Analysis

        """

    pending = []
    text_sample = text_sample.split("\n\n")
    for i, line in enumerate(text_sample):
        text = line.strip()
        if not text:
            continue
        vec, l2norm = embed(text)
        pending.append(
                (str(uuid.uuid4()),
                len(vec),
                vec.astype("float32").tobytes(),
                float(l2norm),
                json.dumps({"text": text}))
        )
        # Commit in batches of 5
        if len(pending) >= 5:
            insert_batch(cur, pending)
            con.commit()
            pending.clear()
            print(f"batch number {i/5}")


    # Final commit
    if pending:
        insert_batch(cur, pending)
        con.commit()
    
    print("finished")

if __name__ == "__main__":
    main()
