"""hacker_news_monitor — auto-generated skill by Wave.

Monitor Hacker News for trending stories, search by keywords, analyze discussions and track tech trends
"""

import httpx
import json
import asyncio
from datetime import datetime

async def get_top_stories(params: dict) -> dict:
    """Get top stories from Hacker News"""
    try:
        limit = params.get('limit', 10)
        
        async with httpx.AsyncClient() as client:
            # Get top story IDs
            response = await client.get('https://hacker-news.firebaseio.com/v0/topstories.json')
            story_ids = response.json()[:limit]
            
            stories = []
            for story_id in story_ids:
                story_response = await client.get(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json')
                story = story_response.json()
                if story and story.get('type') == 'story':
                    stories.append({
                        'id': story.get('id'),
                        'title': story.get('title'),
                        'url': story.get('url'),
                        'score': story.get('score'),
                        'by': story.get('by'),
                        'time': datetime.fromtimestamp(story.get('time', 0)).isoformat(),
                        'descendants': story.get('descendants', 0),  # comment count
                        'hn_url': f"https://news.ycombinator.com/item?id={story.get('id')}"
                    })
            
            return {
                'success': True,
                'data': stories,
                'message': f'Retrieved {len(stories)} top stories from Hacker News'
            }
    
    except Exception as e:
        return {
            'success': False,
            'data': None,
            'message': f'Failed to fetch HN stories: {str(e)}'
        }

async def search_stories(params: dict) -> dict:
    """Search Hacker News stories by keyword"""
    try:
        query = params.get('query', '')
        if not query:
            return {'success': False, 'data': None, 'message': 'Query parameter required'}
        
        # Use HN Algolia search API
        async with httpx.AsyncClient() as client:
            search_url = f'https://hn.algolia.com/api/v1/search?query={query}&tags=story'
            response = await client.get(search_url)
            data = response.json()
            
            stories = []
            for hit in data.get('hits', [])[:10]:  # Limit to 10 results
                stories.append({
                    'id': hit.get('objectID'),
                    'title': hit.get('title'),
                    'url': hit.get('url'),
                    'score': hit.get('points', 0),
                    'by': hit.get('author'),
                    'time': hit.get('created_at'),
                    'descendants': hit.get('num_comments', 0),
                    'hn_url': f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                })
            
            return {
                'success': True,
                'data': {
                    'query': query,
                    'results': stories,
                    'total_hits': data.get('nbHits', 0)
                },
                'message': f'Found {len(stories)} stories matching "{query}"'
            }
    
    except Exception as e:
        return {
            'success': False,
            'data': None,
            'message': f'Search failed: {str(e)}'
        }

async def get_story_comments(params: dict) -> dict:
    """Get comments for a specific HN story"""
    try:
        story_id = params.get('story_id')
        if not story_id:
            return {'success': False, 'data': None, 'message': 'story_id parameter required'}
        
        async with httpx.AsyncClient() as client:
            # Get story details
            story_response = await client.get(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json')
            story = story_response.json()
            
            if not story:
                return {'success': False, 'data': None, 'message': 'Story not found'}
            
            # Get top-level comments
            comment_ids = story.get('kids', [])[:10]  # Limit to 10 top comments
            comments = []
            
            for comment_id in comment_ids:
                comment_response = await client.get(f'https://hacker-news.firebaseio.com/v0/item/{comment_id}.json')
                comment = comment_response.json()
                if comment and comment.get('type') == 'comment':
                    comments.append({
                        'id': comment.get('id'),
                        'by': comment.get('by'),
                        'text': comment.get('text', ''),
                        'time': datetime.fromtimestamp(comment.get('time', 0)).isoformat(),
                        'kids': len(comment.get('kids', []))  # reply count
                    })
            
            return {
                'success': True,
                'data': {
                    'story': {
                        'title': story.get('title'),
                        'score': story.get('score'),
                        'comment_count': story.get('descendants', 0)
                    },
                    'comments': comments
                },
                'message': f'Retrieved {len(comments)} comments for story {story_id}'
            }
    
    except Exception as e:
        return {
            'success': False,
            'data': None,
            'message': f'Failed to get comments: {str(e)}'
        }

async def monitor_keywords(params: dict) -> dict:
    """Monitor HN for specific keywords and track trends"""
    try:
        keywords = params.get('keywords', [])
        if not keywords:
            return {'success': False, 'data': None, 'message': 'keywords parameter required (list)'}
        
        results = {}
        
        async with httpx.AsyncClient() as client:
            for keyword in keywords:
                search_url = f'https://hn.algolia.com/api/v1/search?query={keyword}&tags=story'
                response = await client.get(search_url)
                data = response.json()
                
                # Get recent stories (last 7 days)
                recent_stories = []
                for hit in data.get('hits', [])[:5]:
                    recent_stories.append({
                        'title': hit.get('title'),
                        'score': hit.get('points', 0),
                        'comments': hit.get('num_comments', 0),
                        'time': hit.get('created_at'),
                        'hn_url': f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                    })
                
                results[keyword] = {
                    'total_mentions': data.get('nbHits', 0),
                    'recent_stories': recent_stories
                }
        
        return {
            'success': True,
            'data': results,
            'message': f'Monitored {len(keywords)} keywords on Hacker News'
        }
    
    except Exception as e:
        return {
            'success': False,
            'data': None,
            'message': f'Monitoring failed: {str(e)}'
        }

# Export the tools
TOOLS = [
    {
        'name': 'hn_top_stories',
        'description': 'Get top trending stories from Hacker News',
        'handler': get_top_stories,
        'parameters': {
            'type': 'object',
            'properties': {
                'limit': {
                    'type': 'integer',
                    'description': 'Number of stories to retrieve (default: 10)',
                    'default': 10
                }
            }
        }
    },
    {
        'name': 'hn_search',
        'description': 'Search Hacker News stories by keyword',
        'handler': search_stories,
        'parameters': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'Search query/keyword'
                }
            },
            'required': ['query']
        }
    },
    {
        'name': 'hn_comments',
        'description': 'Get comments for a specific HN story',
        'handler': get_story_comments,
        'parameters': {
            'type': 'object',
            'properties': {
                'story_id': {
                    'type': 'string',
                    'description': 'Hacker News story ID'
                }
            },
            'required': ['story_id']
        }
    },
    {
        'name': 'hn_monitor_keywords',
        'description': 'Monitor HN for specific keywords and track trends',
        'handler': monitor_keywords,
        'parameters': {
            'type': 'object',
            'properties': {
                'keywords': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'List of keywords to monitor'
                }
            },
            'required': ['keywords']
        }
    }
]