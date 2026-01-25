import { BookOpen } from 'lucide-react';

interface DocsLinkProps {
  docsPort?: number;
  className?: string;
  iconOnly?: boolean;
}

/**
 * DocsLink - Link to documentation portal
 * 
 * Dynamically constructs the docs URL based on current hostname.
 * In production, docs are served from the same host on a different port.
 * In development, defaults to localhost.
 * 
 * Port assignments (per DOCKER_DOCS_INTEGRATION.md):
 * - capture-spine: 8002
 * - entityspine: 8012
 * - genai-spine: 8022
 * - feedspine: 8032
 */
export function DocsLink({ 
  docsPort = 7012, 
  className = '', 
  iconOnly = false 
}: DocsLinkProps) {
  const docsUrl = `${window.location.protocol}//${window.location.hostname}:${docsPort}`;

  return (
    <a
      href={docsUrl}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
      title="Documentation"
    >
      <BookOpen className="w-4 h-4" />
      {!iconOnly && <span className="ml-2">Documentation</span>}
    </a>
  );
}

export default DocsLink;
