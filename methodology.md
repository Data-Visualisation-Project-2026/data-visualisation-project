### Data Preparation:

#### Article Extraction

Our goal was to determine if natural language processing (NLP) could reliably identify ideological leanings and framing biases in coverage of the 2026 Iran War. We began by pulling articles from a query on [https://www.mediacloud.org/](https://www.mediacloud.org/), for articles containing a few key words related to the Iran War published between 27 Feb 2026 - 29 Mar 2026. Because this basic keyword search method occasionally introduces unrelated articles, we used an AI-based filtering tool, Sentence Transformers (specifically, all-MiniLM-L12-v2), in order to score articles based on their title in the dataset according to the following positive and negative anchors, such that unrelated articles would be excluded from the dataset:

```
positive_anchors = ['Military conflict, airstrikes, ship sinking, war, and geopolitical tensions involving Iran, the United States or Pentagon, Israel or IDF, and the Middle East.', 'International diplomacy, humanitarian crisis, peace negotiations, and global leaders responding to the war in Iran', 'Iranian government leadership, Supreme Leader Ayatollah Ali Khamenei and Mojtaba Khamenei, and major political figures', 'Reporting on oil and gas prices amid war']
negative_anchors = ['Domestic crime, murder, executions, capital punishment, criminal justice, and local police matters.', 'Weather reports, natural disasters, sports, or local community events.' 'Cartoon, top news']
```

Following this filtering procedure, we reduced the relevant article count from ~53,000 to about ~20,000. We were interested in employing a Local LLM in order to score article texts on a very specific set of dimensions, and in order to deal with this limitation, we had to truncate our sample further. We decided to only include articles from sources which have at least 25 articles on the topic, and to randomly sample 25 articles per source. Accordingly, we ended up extracting text from 1925 articles from 77 different sources. We noticed that this set of articles excluded a few key sources we would like to analyze, and in order to ensure our map of the media landscape was comprehensive, we manually added 1,736 articles from five major missing publications (extending their timeframe to April 15). Using the trafilatura library, we extracted the raw article text from this set of articles, and were ready to proceed to the NLP stage.

#### AI Scoring and Dimensionality

We used a specialized, locally hosted AI model, Gemma 4 E4B (instruction-tuned), to act as an automated media analyst. We prompted the model to read each article and score it from 0.0 to 1.0 across five distinct narrative frames:

These 5 dimensions are:

- kinetic_focus, relating to military hardware and activity generally,
- humanitarian_focus, relating to concerns for the wellbeing of civilians and other disadvantaged groups,
- diplomatic_focus, relating to how the differing parties are interacting,
- economic-focus, relating to the economic impacts of the war, and
- culpability_bias, relating to the extent to which articles use active language and strong verbs to assign moral blame. We would also like to generally examine some of the most high impact words in the sample of articles.

The rationale for this set of scores was to uncover how different media outlets frame their articles according to these distinct categories. We believed that by scoring articles in this way, we could uncover interesting temporal patterns along with interesting media-outlet level clustering patterns. In order to obtain these scores, we used prompt engineering to and low temperature (0.1) to score each article along these 5 axes:

```
You are an expert media analyst extracting ideological framing from conflict reporting. 
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
{article text}
```

This analysis proved valuable with results that largely match general intuition of the media landscape, and so we proceeded with our additional analysis.

#### Limitation

This Gemma processing step took around 40 hours of computation time on a device with an RTX 3070 (8 GB VRAM) and 32 GB of RAM on a quantized version of the Gemma model. With stronger hardware, or a higher budget to use paid APIs, it would be better to extract all of the relevant article text such that the random sample doesn't skew certain outlets a certain way by chance. 25 articles is not necessarily enough to be representative of a media outlet as a whole, and it is possible that we extracted a small set of articles that are more aligned with one axis vs. another.

### Clustering and Network Analysis:

For the clustering step, we merged the two sets of articles into one dataframe, and used Scikit-Learn's KMeans clustering method to Cluster each article along the 5 axes with n clusters set to 5. 5 clusters were chosen because it provided the most interesting and interpretable result. We additionally did outlet-level clustering by averaging the scores along the 5 axes for each outlet, and using the same Scikit-Learn KMeans clustering method. After this, the datasets were split again, so that the clusters are matched at the aggregate level, but separate analysis is still possible given the different ways the data was prepared.

Then, for the network step, we decided to do a 3D visualization via plotly which meant that we needed to use principal component analysis to reduce the 5 dimensions to 3. In doing so, we were able to capture ~86% of the variance in 3 dimensions, and generate a basic scatter plot. The network was built via Scikit-Learn's KNearestNeighbors method to capture the 3 nearest neighbors to each node of the graph. This ensures that every node is connected by at least 3 edges, and allows us to measure the extent to which different media outlets are close to each other between clusters. 

#### Limitation

Because we forced the algorithm to draw exactly three connections per outlet to map the relationships between our pre-defined clusters, this isn't a traditional, organically grown network graph. However, the resulting edges still provide a highly accurate and interpretable representation of which media outlets are closest to one another ideologically.