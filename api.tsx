export async function getArticles() {
  try {
    console.log('Fetching articles with populate=*');
    
    const res = await fetch('http://20.169.90.64:1337/api/articles?populate=*', { 
      headers: { Accept: 'application/json' }, 
      cache: 'no-store',
    }); 
    
    if (!res.ok) {
      throw new Error(`Failed to fetch articles: ${res.status} ${res.statusText}`);
    }
    
    const json = await res.json(); 
    console.log('API response received');
    
    if (!json.data) {
      console.warn('No data field in response');
      return [];
    }
    
    // Transform the data with correct field structure
    const transformedArticles = json.data.map((article: any) => {
      let coverImage = null;
      
      // Handle the cover field structure from your Strapi response
      if (article.cover) {
        console.log(`Found cover image for article ${article.id}:`, article.cover.url);
        
        coverImage = {
          url: article.cover.url,
          alternativeText: article.cover.alternativeText,
          // Also include different sizes if you want to use responsive images
          formats: article.cover.formats
        };
      }
      
      return {
        ...article,
        coverImage
      };
    });
    
    console.log(`Successfully processed ${transformedArticles.length} articles`);
    return transformedArticles;
    
  } catch (error) {
    console.error('Error fetching articles:', error);
    return [];
  }
