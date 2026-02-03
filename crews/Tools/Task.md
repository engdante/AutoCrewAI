# User Task for Agents

### Enhanced Task Description:
**Primary Objective**: Create a comprehensive, professional analysis of FC Barcelona's recent news that is suitable for publication in major sports media outlets. This task requires multi-stage processing involving data collection, expert analysis, and editorial refinement.

**Detailed Requirements**:
1. **Data Collection Phase**:
   - Use the `brave_search` tool to gather the 5 most recent news articles about FC Barcelona from high-authority sources (ESPN, Marca, official club channels, etc.)
   - Extract and structure the following data points for each article:
     * Headline
     * Publication timestamp (ISO format)
     * Source URL
     * Brief description (100-150 characters)
     * Author name (if available)
   - Save this raw data in JSON format to `tool_results.md`
   - Ensure no duplicate content is collected

2. **Analytical Phase**:
   - Process the raw data from `tool_results.md` using `Read a file's content`
   - Categorize news items into one or more of these domains:
     * Player performance (individual statistics, form, injuries)
     * Tactical developments
     * Transfer rumors/speculation
     * Team strategy/coaching changes
     * League standings implications
   - Identify key themes and potential impacts on FC Barcelona's season performance
   - Create a structured analysis document (`analyzed_news.md`) with:
     * Executive summary (150 words)
     * Detailed breakdown of each news item with contextual analysis
     * Cross-article thematic connections
     * Potential implications for team performance

3. **Editorial Refinement Phase**:
   - Review the analytical output from `analyzed_news.md`
   - Ensure all content meets professional journalistic standards:
     * Proper attribution and sourcing
     * Neutral, objective tone with minimal bias
     * Proper grammar, spelling, and punctuation
     * Logical flow between sections
   - Enhance readability through:
     * Subheadings for clear section breaks
     * Concise paragraph structure (average 3-5 sentences)
     * Appropriate use of transitions between ideas
   - Add editorial elements including:
     * Compelling title that reflects content
     * Brief introductory paragraph (200 words) providing context and value proposition
     * Conclusion summarizing key takeaways (100 words)

**Output Specifications**:
- Final document (`final_news_summary.md`) must follow this structure:
  markdown
  # [Compelling Title Reflecting Content]

  **Introduction**
  [200-word paragraph providing context and value proposition]

  **Headline Analysis**
  [Structured breakdown of each news item with analysis]

  **Key Themes & Implications**
  [Thematic connections and potential impacts on team performance]

  **Conclusion**
  [100-word summary of key takeaways]
  

**Quality Assurance Criteria**:
- Content must be original, not copied from source articles
- All assertions must be supported by evidence from the collected data
- Professional tone throughout (avoid colloquial language)
- Proper handling of sensitive topics (rumors, speculation) with clear disclaimers where appropriate
- Visual formatting that enhances readability without excessive design elements

**Success Metrics**:
1. Completion within specified timeframe
2. Adherence to output structure and requirements
3. Depth and quality of analysis (demonstrated through insightful connections between news items)
4. Professionalism in language and presentation
