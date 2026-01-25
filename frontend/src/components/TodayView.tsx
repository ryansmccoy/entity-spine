import { useState } from 'react';
import {
  Clock,
  Star,
  Eye,
  RefreshCw,
  ChevronRight,
  Sparkles,
  Flame,
  ExternalLink,
} from 'lucide-react';
import { clsx } from 'clsx';
import { formatDistanceToNow, format, isToday, isYesterday } from 'date-fns';

// Types
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

interface TodayViewProps {
  latestArticles: Article[];
  popularArticles: Article[];
  starredArticles: Article[];
  recentlyViewed: Article[];
  isLoading?: boolean;
  onRefresh: () => void;
  onSelectArticle: (article: Article) => void;
  onToggleStar: (articleId: string) => void;
}

// Time grouping helper
function getTimeGroup(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);

  if (diffHours < 1) return 'Last Hour';
  if (diffHours < 4) return 'Last 4 Hours';
  if (isToday(date)) return 'Today';
  if (isYesterday(date)) return 'Yesterday';
  return format(date, 'EEEE, MMM d');
}

// Article list item
function ArticleListItem({
  article,
  onSelect,
  onToggleStar,
  showStats = false,
}: {
  article: Article;
  onSelect: () => void;
  onToggleStar: () => void;
  showStats?: boolean;
}) {
  return (
    <div
      onClick={onSelect}
      className={clsx(
        'group flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors',
        'hover:bg-gray-50 dark:hover:bg-gray-800/50',
        article.isRead && 'opacity-60'
      )}
    >
      {/* Feed Icon */}
      <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-lg">
        {article.feedIcon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <h4
            className={clsx(
              'text-sm leading-snug',
              article.isRead
                ? 'text-gray-500 dark:text-gray-400'
                : 'font-medium text-gray-900 dark:text-white'
            )}
          >
            {article.title}
          </h4>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleStar();
            }}
            className={clsx(
              'flex-shrink-0 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity',
              article.isStarred
                ? 'text-yellow-500 opacity-100'
                : 'text-gray-300 hover:text-yellow-500'
            )}
          >
            <Star className={clsx('h-4 w-4', article.isStarred && 'fill-current')} />
          </button>
        </div>

        <div className="flex items-center gap-2 mt-1.5 text-xs text-gray-500 dark:text-gray-400">
          <span>{article.feedName}</span>
          {article.formType && (
            <>
              <span>•</span>
              <span className="font-medium text-primary-600 dark:text-primary-400">{article.formType}</span>
            </>
          )}
          <span>•</span>
          <span>{formatDistanceToNow(article.publishedAt, { addSuffix: true })}</span>
          
          {showStats && (
            <>
              {article.viewCount !== undefined && (
                <>
                  <span>•</span>
                  <span className="flex items-center gap-0.5">
                    <Eye className="h-3 w-3" />
                    {article.viewCount}
                  </span>
                </>
              )}
              {article.starCount !== undefined && (
                <>
                  <span>•</span>
                  <span className="flex items-center gap-0.5">
                    <Star className="h-3 w-3" />
                    {article.starCount}
                  </span>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {/* Open in new tab */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          if (article.url) window.open(article.url, '_blank');
        }}
        className="flex-shrink-0 p-1 text-gray-300 hover:text-gray-500 dark:hover:text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <ExternalLink className="h-4 w-4" />
      </button>
    </div>
  );
}

// Section component
function Section({
  title,
  icon: Icon,
  iconColor,
  children,
  count,
  viewAllHref,
  onViewAll,
}: {
  title: string;
  icon: React.ElementType;
  iconColor: string;
  children: React.ReactNode;
  count?: number;
  viewAllHref?: string;
  onViewAll?: () => void;
}) {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <div className={clsx('p-1.5 rounded-lg', iconColor)}>
            <Icon className="h-4 w-4 text-white" />
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
          {count !== undefined && (
            <span className="text-xs text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-full">
              {count}
            </span>
          )}
        </div>
        {(viewAllHref || onViewAll) && (
          <button
            onClick={onViewAll}
            className="flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium"
          >
            View all
            <ChevronRight className="h-3 w-3" />
          </button>
        )}
      </div>
      <div className="divide-y divide-gray-100 dark:divide-gray-800">{children}</div>
    </div>
  );
}

// Main component
export function TodayView({
  latestArticles,
  popularArticles,
  starredArticles,
  recentlyViewed,
  isLoading = false,
  onRefresh,
  onSelectArticle,
  onToggleStar,
}: TodayViewProps) {
  const [activeTab, setActiveTab] = useState<'latest' | 'popular' | 'starred' | 'recent'>('latest');

  // Group latest articles by time
  const groupedLatest = latestArticles.reduce((acc, article) => {
    const group = getTimeGroup(article.publishedAt);
    if (!acc[group]) acc[group] = [];
    acc[group].push(article);
    return acc;
  }, {} as Record<string, Article[]>);

  const tabs = [
    { id: 'latest', label: 'Latest', icon: Clock, count: latestArticles.length },
    { id: 'popular', label: 'Popular', icon: Flame, count: popularArticles.length },
    { id: 'starred', label: 'Starred', icon: Star, count: starredArticles.length },
    { id: 'recent', label: 'Recent', icon: Eye, count: recentlyViewed.length },
  ] as const;

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary-500" />
            Today
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {format(new Date(), 'EEEE, MMMM d, yyyy')}
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
        >
          <RefreshCw className={clsx('h-4 w-4', isLoading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg mb-6">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors',
                activeTab === tab.id
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
              <span className="text-xs text-gray-400 bg-gray-200 dark:bg-gray-600 px-1.5 rounded">
                {tab.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Content */}
      {activeTab === 'latest' && (
        <div className="space-y-6">
          {Object.entries(groupedLatest).map(([group, articles]) => (
            <Section
              key={group}
              title={group}
              icon={Clock}
              iconColor="bg-blue-500"
              count={articles.length}
            >
              {articles.slice(0, 10).map((article) => (
                <ArticleListItem
                  key={article.id}
                  article={article}
                  onSelect={() => onSelectArticle(article)}
                  onToggleStar={() => onToggleStar(article.id)}
                />
              ))}
            </Section>
          ))}
          
          {latestArticles.length === 0 && (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              <Clock className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="font-medium">No new articles</p>
              <p className="text-sm">Check back later for updates</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'popular' && (
        <Section
          title="Trending This Week"
          icon={Flame}
          iconColor="bg-orange-500"
          count={popularArticles.length}
        >
          {popularArticles.slice(0, 10).map((article, index) => (
            <div key={article.id} className="flex items-center gap-3">
              <div className="w-8 text-center">
                <span
                  className={clsx(
                    'text-lg font-bold',
                    index < 3 ? 'text-orange-500' : 'text-gray-300 dark:text-gray-600'
                  )}
                >
                  {index + 1}
                </span>
              </div>
              <div className="flex-1">
                <ArticleListItem
                  article={article}
                  onSelect={() => onSelectArticle(article)}
                  onToggleStar={() => onToggleStar(article.id)}
                  showStats
                />
              </div>
            </div>
          ))}
          
          {popularArticles.length === 0 && (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              <Flame className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="font-medium">No popular articles yet</p>
              <p className="text-sm">Articles with the most views will appear here</p>
            </div>
          )}
        </Section>
      )}

      {activeTab === 'starred' && (
        <Section
          title="Your Starred Articles"
          icon={Star}
          iconColor="bg-yellow-500"
          count={starredArticles.length}
        >
          {starredArticles.slice(0, 20).map((article) => (
            <ArticleListItem
              key={article.id}
              article={article}
              onSelect={() => onSelectArticle(article)}
              onToggleStar={() => onToggleStar(article.id)}
            />
          ))}
          
          {starredArticles.length === 0 && (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              <Star className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="font-medium">No starred articles</p>
              <p className="text-sm">Star articles to save them for later</p>
            </div>
          )}
        </Section>
      )}

      {activeTab === 'recent' && (
        <Section
          title="Recently Viewed"
          icon={Eye}
          iconColor="bg-purple-500"
          count={recentlyViewed.length}
        >
          {recentlyViewed.slice(0, 20).map((article) => (
            <ArticleListItem
              key={article.id}
              article={article}
              onSelect={() => onSelectArticle(article)}
              onToggleStar={() => onToggleStar(article.id)}
            />
          ))}
          
          {recentlyViewed.length === 0 && (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              <Eye className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="font-medium">No recently viewed articles</p>
              <p className="text-sm">Articles you read will appear here</p>
            </div>
          )}
        </Section>
      )}
    </div>
  );
}

export default TodayView;
