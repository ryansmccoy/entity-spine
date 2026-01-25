import { useState } from 'react';
import { TodayView } from '../components/TodayView';

// Types matching TodayView component
interface Article {
  id: string;
  title: string;
  feedName: string;
  feedIcon: string;
  formType?: string;
  companyName?: string;
  publishedAt: Date;
  isRead: boolean;
  isStarred: boolean;
  viewCount?: number;
  starCount?: number;
  url?: string;
}

// Sample data generator
const generateSampleArticles = (): Article[] => {
  const companies = [
    { name: 'Apple Inc.', ticker: 'AAPL', icon: '🍎' },
    { name: 'Microsoft Corporation', ticker: 'MSFT', icon: '💻' },
    { name: 'NVIDIA Corporation', ticker: 'NVDA', icon: '🎮' },
    { name: 'Amazon.com Inc.', ticker: 'AMZN', icon: '📦' },
    { name: 'Tesla Inc.', ticker: 'TSLA', icon: '⚡' },
    { name: 'Meta Platforms Inc.', ticker: 'META', icon: '👤' },
    { name: 'Alphabet Inc.', ticker: 'GOOGL', icon: '🔍' },
    { name: 'Berkshire Hathaway', ticker: 'BRK.A', icon: '🏢' },
  ];

  const formTypes = ['10-K', '10-Q', '8-K', 'DEF 14A', '4', 'S-1', '13F-HR', 'SC 13G'];
  const articles: Article[] = [];

  for (let i = 0; i < 30; i++) {
    const company = companies[Math.floor(Math.random() * companies.length)];
    const formType = formTypes[Math.floor(Math.random() * formTypes.length)];
    const hoursAgo = Math.floor(Math.random() * 72);
    const publishedAt = new Date(Date.now() - hoursAgo * 60 * 60 * 1000);
    
    articles.push({
      id: `article-${i}`,
      title: `${company.name} (${company.ticker}) - ${formType} Filing`,
      feedName: `SEC ${formType} Filings`,
      feedIcon: company.icon,
      formType: formType,
      companyName: company.name,
      publishedAt,
      isRead: Math.random() > 0.6,
      isStarred: Math.random() > 0.85,
      viewCount: Math.floor(Math.random() * 500) + 10,
      starCount: Math.floor(Math.random() * 50),
      url: `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=${encodeURIComponent(company.name)}`,
    });
  }

  return articles.sort((a, b) => b.publishedAt.getTime() - a.publishedAt.getTime());
};

export function TodayPage() {
  const [allArticles, setAllArticles] = useState<Article[]>(generateSampleArticles);
  const [isLoading, setIsLoading] = useState(false);

  // Derive different article lists
  const latestArticles = allArticles.slice(0, 15);
  
  const popularArticles = [...allArticles]
    .sort((a, b) => (b.viewCount || 0) - (a.viewCount || 0))
    .slice(0, 10);
  
  const starredArticles = allArticles.filter(a => a.isStarred);
  
  const recentlyViewed = allArticles
    .filter(a => a.isRead)
    .slice(0, 10);

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => {
      setAllArticles(generateSampleArticles());
      setIsLoading(false);
    }, 1000);
  };

  const handleSelectArticle = (article: Article) => {
    if (article.url) {
      window.open(article.url, '_blank');
    }
    // Mark as read
    setAllArticles(prev => prev.map(a =>
      a.id === article.id ? { ...a, isRead: true } : a
    ));
  };

  const handleToggleStar = (articleId: string) => {
    setAllArticles(prev => prev.map(a =>
      a.id === articleId ? { ...a, isStarred: !a.isStarred } : a
    ));
  };

  return (
    <div className="p-6">
      <TodayView
        latestArticles={latestArticles}
        popularArticles={popularArticles}
        starredArticles={starredArticles}
        recentlyViewed={recentlyViewed}
        isLoading={isLoading}
        onRefresh={handleRefresh}
        onSelectArticle={handleSelectArticle}
        onToggleStar={handleToggleStar}
      />
    </div>
  );
}

export default TodayPage;
