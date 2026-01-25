import { useState } from 'react';
import {
  X,
  ExternalLink,
  Eye,
  Download,
  Star,
  Clock,
  FileText,
  Building2,
  Hash,
  Calendar,
  Link2,
  Copy,
  Share2,
  Printer,
  Bookmark,
  ChevronDown,
  ChevronUp,
  File,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { clsx } from 'clsx';

interface ArticleData {
  id: string;
  title: string;
  url?: string;
  isStarred: boolean;
  isRead: boolean;
  captured: boolean;
  time: string;
  // SEC-specific fields
  formType?: string;
  cik?: string;
  companyName?: string;
  ticker?: string;
  filingDate?: string;
  acceptedDate?: string;
  accessionNumber?: string;
  // Content
  summary?: string;
  documents?: { name: string; url: string; type: string }[];
  relatedFilings?: { title: string; formType: string; date: string; url: string }[];
}

interface EnhancedPreviewPanelProps {
  article: ArticleData | null;
  onClose: () => void;
  onToggleStar: () => void;
  onCapture?: () => void;
  isCapturing?: boolean;
}

export function EnhancedPreviewPanel({
  article,
  onClose,
  onToggleStar,
  onCapture,
  isCapturing = false,
}: EnhancedPreviewPanelProps) {
  const [showDocuments, setShowDocuments] = useState(true);
  const [showRelated, setShowRelated] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!article) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-8">
        <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
          <FileText className="h-8 w-8 text-gray-400" />
        </div>
        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
          Select an article
        </h4>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Click on an article to preview it here
        </p>
      </div>
    );
  }

  const copyLink = async () => {
    if (article.url) {
      await navigator.clipboard.writeText(article.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const openInNewTab = () => {
    if (article.url) {
      window.open(article.url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <div className="h-full flex flex-col bg-white dark:bg-[#1E1E2D]">
      {/* Header with Action Buttons - MOVED TO TOP */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700">
        {/* Primary Actions Row */}
        <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800/50">
          <div className="flex items-center gap-2">
            <button
              onClick={openInNewTab}
              disabled={!article.url}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-primary-600 hover:bg-primary-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open in New Tab
            </button>
            <button
              onClick={() => article.url && window.open(article.url, 'preview', 'width=1200,height=800')}
              disabled={!article.url}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 rounded disabled:opacity-50"
            >
              <Eye className="h-3.5 w-3.5" />
              Preview Site
            </button>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={copyLink}
              disabled={!article.url}
              className="p-1.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Copy link"
            >
              {copied ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
            </button>
            <button
              className="p-1.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Share"
            >
              <Share2 className="h-4 w-4" />
            </button>
            <button
              className="p-1.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Print"
            >
              <Printer className="h-4 w-4" />
            </button>
            <div className="w-px h-4 bg-gray-300 dark:bg-gray-600 mx-1" />
            <button
              onClick={onToggleStar}
              className={clsx(
                'p-1.5 rounded',
                article.isStarred
                  ? 'text-yellow-500 hover:bg-yellow-50 dark:hover:bg-yellow-900/20'
                  : 'text-gray-400 hover:text-yellow-500 hover:bg-gray-100 dark:hover:bg-gray-700'
              )}
              title={article.isStarred ? 'Remove star' : 'Star article'}
            >
              <Star className={clsx('h-4 w-4', article.isStarred && 'fill-current')} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Close preview"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          {/* Title */}
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white leading-tight mb-3">
            {article.title}
          </h2>

          {/* Meta Info Grid */}
          {(article.companyName || article.formType || article.filingDate) && (
            <div className="grid grid-cols-2 gap-2 mb-4 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-xs">
              {article.companyName && (
                <div className="flex items-center gap-2">
                  <Building2 className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-gray-500 dark:text-gray-400">Company:</span>
                  <span className="font-medium text-gray-900 dark:text-white truncate">{article.companyName}</span>
                </div>
              )}
              {article.ticker && (
                <div className="flex items-center gap-2">
                  <Hash className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-gray-500 dark:text-gray-400">Ticker:</span>
                  <span className="font-medium text-gray-900 dark:text-white">{article.ticker}</span>
                </div>
              )}
              {article.formType && (
                <div className="flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-gray-500 dark:text-gray-400">Form:</span>
                  <span className="font-medium text-primary-600 dark:text-primary-400">{article.formType}</span>
                </div>
              )}
              {article.cik && (
                <div className="flex items-center gap-2">
                  <Hash className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-gray-500 dark:text-gray-400">CIK:</span>
                  <span className="font-mono text-gray-900 dark:text-white">{article.cik}</span>
                </div>
              )}
              {article.filingDate && (
                <div className="flex items-center gap-2">
                  <Calendar className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-gray-500 dark:text-gray-400">Filed:</span>
                  <span className="font-medium text-gray-900 dark:text-white">{article.filingDate}</span>
                </div>
              )}
              {article.accessionNumber && (
                <div className="flex items-center gap-2 col-span-2">
                  <Link2 className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-gray-500 dark:text-gray-400">Accession:</span>
                  <span className="font-mono text-xs text-gray-900 dark:text-white">{article.accessionNumber}</span>
                </div>
              )}
            </div>
          )}

          {/* Time */}
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mb-4">
            <Clock className="h-3.5 w-3.5" />
            <span>{article.time}</span>
            {article.isRead && (
              <>
                <span>•</span>
                <span className="text-green-600 dark:text-green-400">Read</span>
              </>
            )}
          </div>

          {/* Content Section */}
          {article.captured ? (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              {article.summary ? (
                <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                  {article.summary}
                </p>
              ) : (
                <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                  This filing has been captured and is ready for viewing. Click "Read Full Article" below
                  to access the complete content in a clean reader view.
                </p>
              )}
            </div>
          ) : (
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-1">
                    Content not yet captured
                  </h4>
                  <p className="text-xs text-amber-700 dark:text-amber-300 mb-3">
                    The full content of this filing hasn't been captured yet. You can capture it now
                    to read it offline or wait for the next scheduled capture.
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={onCapture}
                      disabled={isCapturing}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-amber-600 hover:bg-amber-700 rounded disabled:opacity-50"
                    >
                      {isCapturing ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          Capturing...
                        </>
                      ) : (
                        <>
                          <Download className="h-3.5 w-3.5" />
                          Capture Now
                        </>
                      )}
                    </button>
                    <span className="text-xs text-amber-600 dark:text-amber-400">
                      Est. time: ~5 seconds
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Documents Section */}
          {article.documents && article.documents.length > 0 && (
            <div className="mt-4">
              <button
                onClick={() => setShowDocuments(!showDocuments)}
                className="flex items-center justify-between w-full text-left text-sm font-medium text-gray-900 dark:text-white mb-2"
              >
                <span>Filing Documents ({article.documents.length})</span>
                {showDocuments ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
              {showDocuments && (
                <div className="space-y-1">
                  {article.documents.map((doc, i) => (
                    <a
                      key={i}
                      href={doc.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 p-2 text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded"
                    >
                      <File className="h-4 w-4 text-gray-400" />
                      <span className="flex-1 truncate">{doc.name}</span>
                      <span className="text-gray-400 uppercase">{doc.type}</span>
                      <ExternalLink className="h-3 w-3 text-gray-400" />
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Related Filings */}
          {article.relatedFilings && article.relatedFilings.length > 0 && (
            <div className="mt-4">
              <button
                onClick={() => setShowRelated(!showRelated)}
                className="flex items-center justify-between w-full text-left text-sm font-medium text-gray-900 dark:text-white mb-2"
              >
                <span>Related Filings ({article.relatedFilings.length})</span>
                {showRelated ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
              {showRelated && (
                <div className="space-y-1">
                  {article.relatedFilings.map((filing, i) => (
                    <a
                      key={i}
                      href={filing.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 p-2 text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded"
                    >
                      <span className="font-medium text-primary-600">{filing.formType}</span>
                      <span className="flex-1 truncate">{filing.title}</span>
                      <span className="text-gray-400">{filing.date}</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Actions */}
      <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 p-3">
        <div className="flex gap-2">
          {article.captured ? (
            <button className="flex-1 btn btn-primary flex items-center justify-center gap-2 h-9 text-sm">
              <Eye className="h-4 w-4" />
              Read Full Article
            </button>
          ) : (
            <button
              onClick={onCapture}
              disabled={isCapturing}
              className="flex-1 btn btn-primary flex items-center justify-center gap-2 h-9 text-sm"
            >
              {isCapturing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Capturing...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  Capture Content
                </>
              )}
            </button>
          )}
          <button className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
            <Bookmark className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default EnhancedPreviewPanel;
