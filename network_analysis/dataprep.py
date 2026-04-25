# -*- coding: utf-8 -*-
"""
Created on Sat Apr  4 14:23:17 2026

@author: Max
"""

import pandas as pd
import trafilatura
import time
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util
import torch
import json
import re
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, pipeline
import transformers
transformers.logging.set_verbosity_error()
import os

'''
# Loading the data into a pandas DataFrame
df = pd.read_csv('./data/mc-onlinenews-mediacloud-20260330180736-content.csv')
df = df.dropna(subset=['title']).copy()

# Because many of the articles scraped are not actually related to the Iran war, I am going to run a small sentence similarity model to find titles that are clearly related to the Iran war
model = SentenceTransformer('all-MiniLM-L12-v2')

positive_anchors = ['Military conflict, airstrikes, ship sinking, war, and geopolitical tensions involving Iran, the United States or Pentagon, Israel or IDF, and the Middle East.',
                    'International diplomacy, humanitarian crisis, peace negotiations, and global leaders responding to the war in Iran',
                    'Iranian government leadership, Supreme Leader Ayatollah Ali Khamenei and Mojtaba Khamenei, and major political figures',
                    'Reporting on oil and gas prices amid war']
negative_anchors = ['Domestic crime, murder, executions, capital punishment, criminal justice, and local police matters.',
                    'Weather reports, natural disasters, sports, or local community events.'
                    'Cartoon, top news']

positive_embedding = model.encode(positive_anchors, convert_to_tensor=True)
negative_embedding = model.encode(negative_anchors, convert_to_tensor=True)

title_embeddings = model.encode(df['title'].tolist(), convert_to_tensor=True, show_progress_bar=True)
pos_scores = util.cos_sim(title_embeddings, positive_embedding).cpu().numpy().max(axis=1)
neg_scores = util.cos_sim(title_embeddings, negative_embedding).cpu().numpy().max(axis=1)

# Adding the relevance scores to the df
df['positive_score'] = pos_scores
df['negative_score'] = neg_scores

# Filtering to only include mostly relevant articles that don't have a negative score greater than the positive score
threshold = 0.35
df_relevant = df[(df['positive_score'] >= threshold) & (df['positive_score'] > df['negative_score'])]

df_relevant.to_csv('./data/filtered_iran_articles.csv', index=False)
'''
'''
df = pd.read_csv('./data/filtered_iran_articles.csv')

# Scraping all article texts from the DataFrame of articles relevant to Iran
article_texts = []
for url in tqdm(df['url'], desc="Scraping Articles"):
    try:
        downloaded = trafilatura.fetch_url(url)
        
        if downloaded is not None:
            text = trafilatura.extract(downloaded)
            article_texts.append(text)
        else:
            article_texts.append(None)
            
    except Exception as e:
        article_texts.append(None)
    
    time.sleep(0.5)

df['article_text'] = article_texts

df_clean = df.dropna(subset=['article_text'])

df_clean.to_csv('./data/scraped_articles.csv', index=False)
'''

# Sampling 25 articles from sources which have at least 25 articles on the topic
df = pd.read_csv('./data/scraped_articles2.csv')
#counts = df['media_name'].value_counts()

#valid_outlets = counts[counts >= 25].index
#df_filtered = df[df['media_name'].isin(valid_outlets)]

#sampled_df = df_filtered.groupby('media_name').sample(n=25, random_state=5)

checkpoint_path = './data/iran_war_backup_checkpoint2.csv'

if os.path.exists(checkpoint_path):
    checkpoint_df = pd.read_csv(checkpoint_path)
    completed_count = len(checkpoint_df)
    tqdm.write(f"Checkpoint with {completed_count} articles. Resuming.")
        
#    remaining_df = sampled_df.iloc[completed_count:].copy()
    remaining_df = df.iloc[completed_count:].copy()
    
    scores_data = {
        'kinetic_focus': checkpoint_df['kinetic_focus'].tolist(),
        'humanitarian_focus': checkpoint_df['humanitarian_focus'].tolist(),
        'diplomatic_focus': checkpoint_df['diplomatic_focus'].tolist(),
        'economic_focus': checkpoint_df['economic_focus'].tolist(),
        'culpability_bias': checkpoint_df['culpability_bias'].tolist()}
else:
    tqdm.write("No checkpoint found. Starting from scratch...")
    completed_count = 0
#    remaining_df = sampled_df.copy()
    remaining_df = df.copy()
    scores_data = {
        'kinetic_focus': [],
        'humanitarian_focus': [],
        'diplomatic_focus': [],
        'economic_focus': [],
        'culpability_bias': []}

# Quantizing so the model can well run on my hardware
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type='nf4')

# Selecting Google's new Gemma 4 E4B instruction tuned model
model_id = 'google/gemma-4-E4B-it'
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=quantization_config,
    device_map='auto',
    attn_implementation='sdpa')

def build_prompt(article_text):
    # Truncating text slightly to ensure it fits in the context window, then feeding it into a prompt I generated with AI to score each article across different frames
    truncated_text = str(article_text)[:10000]
    return f'''You are an expert media analyst extracting ideological framing from conflict reporting. 
Read the following article and score the presence of the following five narrative frames on a scale of 0.0 to 1.0.

1. kinetic_focus: Emphasis on military hardware, strategy, and strikes.
2. humanitarian_focus: Emphasis on civilian suffering, refugees, and casualties.
3. diplomatic_focus: Emphasis on treaties, international organizations, and negotiations.
4. economic_focus: Emphasis on global trade, oil, and markets.
5. culpability_bias: The degree to which the text uses active voice and strong verbs to assign moral blame.

Output ONLY valid JSON in the exact format below, with no markdown formatting or extra text:
{{
  "kinetic_focus": 0.0,
  "humanitarian_focus": 0.0,
  "diplomatic_focus": 0.0,
  "economic_focus": 0.0,
  "culpability_bias": 0.0
}}

Article Text:
{truncated_text}'''

generator = pipeline(
    'text-generation',
    model=model,
    tokenizer=tokenizer,
    device_map='auto')

#for text in tqdm(remaining_df['article_text'], initial=completed_count, total=len(sampled_df)):
for text in tqdm(remaining_df['article_text'], initial=completed_count, total=len(df)):
    raw_prompt = build_prompt(text)
    chat_format = [{'role': 'user', 'content': raw_prompt}]
    prompt = tokenizer.apply_chat_template(
        chat_format, 
        tokenize=False, 
        add_generation_prompt=True)
    
    output = generator(
        prompt, 
        max_new_tokens=75,
        max_length=None,
        temperature=0.1,
        return_full_text=False)
    
    response_text = output[0]['generated_text']
    
    # Extracting json with regex
    match = re.search(r'\{.*?\}', response_text, re.DOTALL)
    if match:
        try:
            clean_json_string = match.group(0).replace("'", '"')
            parsed_json = json.loads(clean_json_string)
            for key in scores_data.keys():
                scores_data[key].append(parsed_json.get(key, None))
            tqdm.write(f"{parsed_json}")
        except json.JSONDecodeError as e:
            for key in scores_data.keys():
                scores_data[key].append(None)
            tqdm.write(f"JSON Decode Failed: {e}")
            tqdm.write(f"Raw Output: {response_text}\n")
    else:
        for key in scores_data.keys():
            scores_data[key].append(None)
        tqdm.write("No JSON found in output.")
        tqdm.write(f"Raw Output: {response_text}\n")
    
    current_index = len(scores_data['kinetic_focus'])
    if current_index % 50 == 0:
#        temp_df = sampled_df.iloc[:current_index].copy()
        temp_df = df.iloc[:current_index].copy()
        for key, values_list in scores_data.items():
            temp_df[key] = values_list
            
        temp_df.to_csv('./data/iran_war_backup_checkpoint2.csv', index=False)
        tqdm.write(f">>> Checkpoint saved at {current_index} articles <<<")

for key, values_list in scores_data.items():
    #sampled_df[key] = values_list
    df[key] = values_list

#df_final = sampled_df.dropna(subset=['kinetic_focus', 'humanitarian_focus', 'diplomatic_focus', 'economic_focus', 'culpability_bias'])
df_final = df.dropna(subset=['kinetic_focus', 'humanitarian_focus', 'diplomatic_focus', 'economic_focus', 'culpability_bias'])
df_final.to_csv('iran_war_media_framing_scores2.csv', index=False)
df_final.to_parquet('iran_war_media_framing_scores2.parquet', engine='pyarrow')

df_test = pd.read_parquet('iran_war_media_framing_scores2.parquet')
