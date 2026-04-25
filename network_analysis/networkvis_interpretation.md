The results of the clustering algorithm and network construction by building edges between the 3 closest neighbors of a given source provide fascinating interpretable results. Below is a proposed set of interpretations for each cluster:

* **Cluster 0: The Mainstream Center.** This group contains large national outlets and local papers that lack a strong ideological slant regarding the Iran War. They score moderately across the board, without leaning heavily into any single type of framing.

* **Cluster 1: The Dissident/Resistance Wing.** Comprised mostly of outlets highly critical of or resistant to the war (with mainstream outliers like The New York Times). This cluster is defined by high "culpability bias," meaning their coverage focuses heavily on assigning blame or responsibility.

* **Cluster 2: The Diplomatic/Humanitarian Focus.** Featuring a mix of smaller and mainstream sources, this group looks similar to the Mainstream Center at first glance. However, these outlets score much higher on diplomatic and humanitarian framing, suggesting a mainstream coalition that leans slightly against the war.

* **Cluster 3: The Economic Lens.** A highly distinct group made up of business and financial outlets. Unsurprisingly, their coverage is defined almost entirely by a high economic focus.

* **Cluster 4: The Military/Right-Wing Faction.** Made up of military publications, well-known right-wing outlets, and tabloids. Their coverage is heavily defined by a "kinetic focus" (a focus on combat and military action) alongside higher-than-average culpability bias.


Beyond the clusters themselves, analyzing the network's structure reveals which outlets act as the "core" of the conversation and which act as vital "bridges" between different ideologies: 

* **The Core Baseline (Eigenvector Centrality):** The Chicago Tribune, Newsday, and Mercury News are the most deeply embedded outlets in the network. Because they sit tightly packed at the dead center of the Mainstream cluster, their framing represents the ultimate, highly connected baseline for how the war is being covered.

* **The Ideological Bridges (Betweenness Centrality):** Central Maine, the Sun Sentinel, and Vox News act as the vital glue connecting opposing sides of the graph.

  * Central Maine sits exactly on the border of Clusters 0, 1, and 2, linking the mainstream to the dissident and humanitarian wings.

  * The Sun Sentinel acts as the primary bridge connecting the Business faction to the rest of the mainstream.

  * Fascinatingly, Vox News acts as the primary bridge to the Right-Wing/Military faction. It is highly notable that generally left-leaning sources like Vox and The Atlantic are using framing that mathematically bridges the gap to right-aligned media.

* **The Broadest Appeal (Degree Centrality):** The Chicago Tribune, Sun Sentinel, and Al Jazeera have the highest volume of direct connections, meaning their specific framing overlaps with the broadest number of immediate peers within their respective areas.