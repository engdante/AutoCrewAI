"""
Tools Registry for CrewAI Project
=================================

This registry defines available tools for CrewAI agents, including only the tools
that actually exist in the crewai-tools package. Each tool includes metadata for
intelligent selection and integration.

Based on official CrewAI Tools documentation:
https://docs.crewai.com/tools
"""

# Available tools from crewai-tools package
SEARCH_TOOLS = {
    'serper_dev': {
        'name': 'SerperDevTool',
        'class': 'SerperDevTool',
        'description': 'A specialized tool for development purposes, with specific functionalities for web search using Google Search API',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools', 'SERPER_API_KEY'],
        'cost': 'free tier available',
        'suitable_for': ['researcher', 'analyst', 'assistant'],
        'context_triggers': ['google search', 'web search', 'search', 'find', 'research', 'information', 'current', 'latest'],
        'testing_notes': 'Not yet tested - requires SERPER_API_KEY',
        'status': 'untested'
    },
    'website_search': {
        'name': 'WebsiteSearchTool',
        'class': 'WebsiteSearchTool',
        'description': 'A RAG tool for searching website content, optimized for web data extraction',
        'availability': 'confirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'analyst', 'content_writer'],
        'context_triggers': ['website', 'site:', 'domain', 'specific source', 'website content'],
        'testing_notes': 'Confirmed available in crewai-tools',
        'status': 'confirmed'
    },
    'firecrawl_search': {
        'name': 'FirecrawlSearchTool',
        'class': 'FirecrawlSearchTool',
        'description': 'A tool to search webpages using Firecrawl and return the results',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools', 'FIRECRAWL_API_KEY'],
        'cost': 'free tier available',
        'suitable_for': ['researcher', 'analyst'],
        'context_triggers': ['firecrawl', 'web search', 'webpage search'],
        'testing_notes': 'Not yet tested - requires FIRECRAWL_API_KEY',
        'status': 'untested'
    },
    'scrape_website': {
        'name': 'ScrapeWebsiteTool',
        'class': 'ScrapeWebsiteTool',
        'description': 'Facilitates scraping entire websites, ideal for comprehensive data collection',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'analyst', 'content_writer'],
        'context_triggers': ['scrape website', 'scrape entire website', 'website data collection'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'scrape_element': {
        'name': 'ScrapeElementFromWebsiteTool',
        'class': 'ScrapeElementFromWebsiteTool',
        'description': 'Enables scraping specific elements from websites, useful for targeted data extraction',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'analyst', 'content_writer'],
        'context_triggers': ['scrape element', 'extract element', 'targeted data extraction'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    }
}

FILE_TOOLS = {
    'file_reader': {
        'name': 'FileReadTool',
        'class': 'FileReadTool',
        'description': 'Enables reading and extracting data from files, supporting various file formats',
        'availability': 'confirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'analyst', 'assistant', 'writer'],
        'context_triggers': ['file', 'read file', 'extract data', 'file content', 'document'],
        'testing_notes': 'Confirmed available in crewai-tools',
        'status': 'confirmed'
    },
    'directory_reader': {
        'name': 'DirectoryReadTool',
        'class': 'DirectoryReadTool',
        'description': 'Facilitates reading and processing of directory structures and their contents',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'analyst', 'assistant'],
        'context_triggers': ['directory', 'folder', 'read directory', 'process directory'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'pdf_search': {
        'name': 'PDFSearchTool',
        'class': 'PDFSearchTool',
        'description': 'A RAG tool aimed at searching within PDF documents, ideal for processing scanned documents',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'analyst', 'assistant'],
        'context_triggers': ['PDF', 'pdf document', 'search pdf', 'scanned document'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'docx_search': {
        'name': 'DOCXSearchTool',
        'class': 'DOCXSearchTool',
        'description': 'A RAG tool aimed at searching within DOCX documents, ideal for processing Word files',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'analyst', 'writer'],
        'context_triggers': ['DOCX', 'word document', 'word file', 'document processing'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'csv_search': {
        'name': 'CSVSearchTool',
        'class': 'CSVSearchTool',
        'description': 'A RAG tool designed for searching within CSV files, tailored to handle structured data',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['analyst', 'researcher', 'assistant'],
        'context_triggers': ['CSV', 'data analysis', 'structured data', 'table', 'spreadsheet'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'txt_search': {
        'name': 'TXTSearchTool',
        'class': 'TXTSearchTool',
        'description': 'A RAG tool focused on searching within text (.txt) files, suitable for unstructured data',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'analyst', 'assistant'],
        'context_triggers': ['text file', 'txt', 'unstructured data', 'plain text'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'json_search': {
        'name': 'JSONSearchTool',
        'class': 'JSONSearchTool',
        'description': 'A RAG tool designed for searching within JSON files, catering to structured data handling',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['analyst', 'researcher', 'developer'],
        'context_triggers': ['JSON', 'structured data', 'api data', 'configuration'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'mdx_search': {
        'name': 'MDXSearchTool',
        'class': 'MDXSearchTool',
        'description': 'A RAG tool tailored for searching within Markdown (MDX) files, useful for documentation',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'writer', 'developer'],
        'context_triggers': ['markdown', 'mdx', 'documentation', 'readme'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'xml_search': {
        'name': 'XMLSearchTool',
        'class': 'XMLSearchTool',
        'description': 'A RAG tool designed for searching within XML files, suitable for structured data formats',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['analyst', 'developer', 'researcher'],
        'context_triggers': ['XML', 'structured data', 'configuration files', 'markup'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'directory_search': {
        'name': 'DirectorySearchTool',
        'class': 'DirectorySearchTool',
        'description': 'A RAG tool for searching within directories, useful for navigating through file systems',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'analyst', 'developer'],
        'context_triggers': ['directory search', 'file system', 'navigate files', 'folder structure'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    }
}

DATA_TOOLS = {
    'youtube_video_search': {
        'name': 'YoutubeVideoSearchTool',
        'class': 'YoutubeVideoSearchTool',
        'description': 'A RAG tool aimed at searching within YouTube videos, ideal for video data extraction',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'content_writer', 'analyst'],
        'context_triggers': ['youtube video', 'video search', 'video content', 'youtube'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'youtube_channel_search': {
        'name': 'YoutubeChannelSearchTool',
        'class': 'YoutubeChannelSearchTool',
        'description': 'A RAG tool for searching within YouTube channels, useful for video content analysis',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'content_writer', 'analyst'],
        'context_triggers': ['youtube channel', 'channel search', 'channel content', 'youtube analysis'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'code_interpreter': {
        'name': 'CodeInterpreterTool',
        'class': 'CodeInterpreterTool',
        'description': 'A tool for interpreting python code',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['developer', 'analyst', 'researcher'],
        'context_triggers': ['python code', 'code interpretation', 'execute code', 'run python'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'github_search': {
        'name': 'GithubSearchTool',
        'class': 'GithubSearchTool',
        'description': 'A RAG tool for searching within GitHub repositories, useful for code and documentation search',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['developer', 'researcher', 'analyst'],
        'context_triggers': ['github', 'repository', 'code search', 'documentation search'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'rag_tool': {
        'name': 'RagTool',
        'class': 'RagTool',
        'description': 'A general-purpose RAG tool capable of handling various data sources and types',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['researcher', 'analyst', 'assistant'],
        'context_triggers': ['RAG', 'retrieval augmented generation', 'general search', 'multi-source'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    },
    'code_docs_search': {
        'name': 'CodeDocsSearchTool',
        'class': 'CodeDocsSearchTool',
        'description': 'A RAG tool optimized for searching through code documentation and related technical documents',
        'availability': 'unconfirmed',
        'requirements': ['crewai-tools'],
        'cost': 'free',
        'suitable_for': ['developer', 'researcher', 'analyst'],
        'context_triggers': ['code documentation', 'technical docs', 'programming docs', 'developer docs'],
        'testing_notes': 'Not yet tested',
        'status': 'untested'
    }
}

# Master registry combining all tools
ALL_TOOLS = {
    **SEARCH_TOOLS,
    **FILE_TOOLS,
    **DATA_TOOLS
}

def get_tools_by_category(category):
    """Get all tools from a specific category."""
    if category == 'search':
        return SEARCH_TOOLS
    elif category == 'file':
        return FILE_TOOLS
    elif category == 'data':
        return DATA_TOOLS
    else:
        return {}

def get_tool_by_name(tool_name):
    """Get a specific tool by its name."""
    return ALL_TOOLS.get(tool_name)

def get_tools_for_agent_role(agent_role):
    """Get all suitable tools for a specific agent role."""
    suitable_tools = []
    for tool_name, tool_info in ALL_TOOLS.items():
        if agent_role.lower() in [role.lower() for role in tool_info['suitable_for']]:
            suitable_tools.append(tool_name)
    return suitable_tools

def get_tools_by_context_keywords(text):
    """Get tools based on context keywords in the text."""
    suitable_tools = []
    text_lower = text.lower()
    
    for tool_name, tool_info in ALL_TOOLS.items():
        for trigger in tool_info['context_triggers']:
            if trigger in text_lower:
                suitable_tools.append(tool_name)
                break  # Add tool once even if multiple triggers match
    
    return suitable_tools

def get_available_tools():
    """Get all tools that are confirmed to be available."""
    return {name: info for name, info in ALL_TOOLS.items() 
            if info['availability'] == 'confirmed'}

def get_untested_tools():
    """Get all tools that haven't been tested yet."""
    return {name: info for name, info in ALL_TOOLS.items() 
            if info['status'] == 'untested'}

def update_tool_status(tool_name, status, notes=None):
    """Update the testing status of a tool."""
    if tool_name in ALL_TOOLS:
        ALL_TOOLS[tool_name]['status'] = status
        if notes:
            ALL_TOOLS[tool_name]['testing_notes'] = notes

def print_tool_info(tool_name):
    """Print detailed information about a specific tool."""
    tool = get_tool_by_name(tool_name)
    if tool:
        print(f"\n=== {tool['name']} ===")
        print(f"Class: {tool['class']}")
        print(f"Description: {tool['description']}")
        print(f"Availability: {tool['availability']}")
        print(f"Requirements: {', '.join(tool['requirements'])}")
        print(f"Cost: {tool['cost']}")
        print(f"Suitable for: {', '.join(tool['suitable_for'])}")
        print(f"Context triggers: {', '.join(tool['context_triggers'])}")
        print(f"Testing notes: {tool['testing_notes']}")
        print(f"Status: {tool['status']}")
    else:
        print(f"Tool '{tool_name}' not found in registry.")

def print_all_tools():
    """Print information about all tools in the registry."""
    print("\n=== TOOLS REGISTRY ===")
    for category, tools in {
        'Search Tools': SEARCH_TOOLS,
        'File Tools': FILE_TOOLS,
        'Data Tools': DATA_TOOLS
    }.items():
        print(f"\n--- {category} ---")
        for tool_name in tools:
            print(f"  - {tool_name}: {tools[tool_name]['status']}")

if __name__ == "__main__":
    # Example usage
    print_all_tools()
    print(f"\nTools suitable for 'researcher': {get_tools_for_agent_role('researcher')}")
    print(f"Tools triggered by 'search web for information': {get_tools_by_context_keywords('search web for information')}")