/**
 * AI Graph Assistant Component (Level 4 Feature)
 * 
 * Provides natural language interface for graph exploration:
 * - "Show me NVIDIA's supply chain"
 * - "Find path between Apple and TSMC"
 * - "What competitors does AMD have?"
 * - "Highlight all investors"
 */

import { useState, useRef, useEffect } from 'react';
import type { EntityNode, GraphData } from '../../types/graph';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  actions?: GraphAction[];
}

interface GraphAction {
  type: 'highlight' | 'filter' | 'zoom' | 'path' | 'expand';
  label: string;
  payload: Record<string, unknown>;
}

interface AIAssistantProps {
  graphData: GraphData;
  onHighlightNodes: (nodeIds: string[]) => void;
  onZoomToNode: (nodeId: string) => void;
  onFilterChange: (filter: Record<string, unknown>) => void;
  onFindPath: (sourceId: string, targetId: string) => void;
  selectedNode: EntityNode | null;
}

// Simulated AI responses - In production, this would call an LLM API
const RESPONSE_TEMPLATES: Record<string, { message: string; actions: GraphAction[] }> = {
  'supply chain': {
    message: "I've highlighted the supply chain relationships. You can see suppliers in green arrows and customers in purple.",
    actions: [
      { type: 'filter', label: 'Show Suppliers', payload: { relationshipTypes: ['supplier', 'foundry'] } },
    ],
  },
  'competitors': {
    message: "Here are the competitive relationships in the graph. Red edges show direct competition.",
    actions: [
      { type: 'filter', label: 'Show Competition', payload: { relationshipTypes: ['competitor'] } },
    ],
  },
  'investors': {
    message: "I've highlighted all investor entities and their investment relationships.",
    actions: [
      { type: 'filter', label: 'Show Investors', payload: { entityTypes: ['investor'] } },
    ],
  },
  'path': {
    message: "I'll find the shortest path between those entities. Click the button below.",
    actions: [
      { type: 'path', label: 'Find Path', payload: {} },
    ],
  },
  'largest': {
    message: "Here are the entities sized by market cap. Larger nodes = higher market cap.",
    actions: [
      { type: 'highlight', label: 'Size by Market Cap', payload: { sizeBy: 'marketCap' } },
    ],
  },
};

export function AIAssistant({
  graphData,
  onHighlightNodes,
  onZoomToNode,
  onFilterChange,
  onFindPath,
  selectedNode,
}: AIAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: `👋 Hi! I'm your graph assistant. I can help you explore the entity network. Try asking:

• "Show me NVIDIA's supply chain"
• "Find investors in the graph"
• "What are AMD's competitors?"
• "Find path from Apple to ASML"
• "Highlight the largest companies"`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle sending a message
  const handleSend = async () => {
    if (!input.trim() || isThinking) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsThinking(true);

    // Simulate AI thinking
    await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 700));

    // Process the query and generate response
    const response = processQuery(input.toLowerCase(), graphData, selectedNode);
    
    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: response.message,
      timestamp: new Date(),
      actions: response.actions,
    };

    setMessages(prev => [...prev, assistantMessage]);
    setIsThinking(false);
  };

  // Execute an action from the assistant
  const executeAction = (action: GraphAction) => {
    switch (action.type) {
      case 'highlight':
        if (action.payload.nodeIds) {
          onHighlightNodes(action.payload.nodeIds as string[]);
        }
        break;
      case 'filter':
        onFilterChange(action.payload);
        break;
      case 'zoom':
        if (action.payload.nodeId) {
          onZoomToNode(action.payload.nodeId as string);
        }
        break;
      case 'path':
        if (action.payload.sourceId && action.payload.targetId) {
          onFindPath(action.payload.sourceId as string, action.payload.targetId as string);
        }
        break;
    }
  };

  // Suggested queries based on context
  const suggestions = getSuggestions(selectedNode, graphData);

  return (
    <div className="flex flex-col h-full bg-gray-800">
      {/* Header */}
      <div className="p-3 border-b border-gray-700 flex items-center gap-2">
        <span className="text-xl">🤖</span>
        <h2 className="font-semibold">AI Assistant</h2>
        <span className="text-xs bg-purple-600 px-2 py-0.5 rounded">Beta</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map(msg => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-100'
              }`}
            >
              <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
              
              {/* Action buttons */}
              {msg.actions && msg.actions.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {msg.actions.map((action, i) => (
                    <button
                      key={i}
                      onClick={() => executeAction(action)}
                      className="bg-blue-500 hover:bg-blue-600 text-white text-xs px-3 py-1 rounded-full transition-colors"
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              )}
              
              <div className="text-xs text-gray-400 mt-1">
                {msg.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}

        {/* Thinking indicator */}
        {isThinking && (
          <div className="flex justify-start">
            <div className="bg-gray-700 rounded-lg px-3 py-2">
              <div className="flex items-center gap-2">
                <div className="animate-pulse">🤔</div>
                <span className="text-sm text-gray-300">Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && !isThinking && (
        <div className="px-3 pb-2">
          <div className="text-xs text-gray-500 mb-1">Suggestions:</div>
          <div className="flex flex-wrap gap-1">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => setInput(s)}
                className="text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 px-2 py-1 rounded transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-3 border-t border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="Ask about the graph..."
            className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            disabled={isThinking}
          />
          <button
            onClick={handleSend}
            disabled={isThinking || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed px-4 py-2 rounded text-sm transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

// Process user query and generate response
function processQuery(
  query: string,
  graphData: GraphData,
  _selectedNode: EntityNode | null
): { message: string; actions: GraphAction[] } {
  // Reserved for context-aware suggestions based on selected node
  void _selectedNode;
  
  // Check for entity mentions
  const mentionedEntity = graphData.nodes.find(n =>
    query.includes(n.name.toLowerCase()) || query.includes(n.id.toLowerCase())
  );

  // Path finding queries
  if (query.includes('path') || query.includes('connect')) {
    const fromMatch = query.match(/from\s+(\w+)/);
    const toMatch = query.match(/to\s+(\w+)/);
    
    if (fromMatch && toMatch) {
      const fromNode = graphData.nodes.find(n => 
        n.name.toLowerCase().includes(fromMatch[1]) || n.id === fromMatch[1]
      );
      const toNode = graphData.nodes.find(n =>
        n.name.toLowerCase().includes(toMatch[1]) || n.id === toMatch[1]
      );
      
      if (fromNode && toNode) {
        return {
          message: `Finding path from ${fromNode.name} to ${toNode.name}...`,
          actions: [
            { type: 'path', label: `Find Path`, payload: { sourceId: fromNode.id, targetId: toNode.id } },
          ],
        };
      }
    }
    
    return {
      message: "To find a path, please specify both entities. For example: 'Find path from Apple to TSMC'",
      actions: [],
    };
  }

  // Supply chain queries
  if (query.includes('supply') || query.includes('supplier') || query.includes('foundry')) {
    if (mentionedEntity) {
      const suppliers = graphData.links.filter(l => {
        const targetId = typeof l.target === 'string' ? l.target : l.target.id;
        return targetId === mentionedEntity.id && (l.type === 'supplier' || l.type === 'foundry');
      }).map(l => typeof l.source === 'string' ? l.source : l.source.id);

      return {
        message: `${mentionedEntity.name} has ${suppliers.length} suppliers/foundries in the graph.`,
        actions: [
          { type: 'highlight', label: 'Highlight Suppliers', payload: { nodeIds: [mentionedEntity.id, ...suppliers] } },
          { type: 'zoom', label: `Focus on ${mentionedEntity.name}`, payload: { nodeId: mentionedEntity.id } },
        ],
      };
    }
    return RESPONSE_TEMPLATES['supply chain'];
  }

  // Competitor queries
  if (query.includes('competitor') || query.includes('compete') || query.includes('rival')) {
    if (mentionedEntity) {
      const competitors = graphData.links.filter(l => {
        const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
        const targetId = typeof l.target === 'string' ? l.target : l.target.id;
        return l.type === 'competitor' && (sourceId === mentionedEntity.id || targetId === mentionedEntity.id);
      }).map(l => {
        const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
        return sourceId === mentionedEntity.id
          ? (typeof l.target === 'string' ? l.target : l.target.id)
          : sourceId;
      });

      return {
        message: `${mentionedEntity.name} competes with ${competitors.length} entities.`,
        actions: [
          { type: 'highlight', label: 'Highlight Competitors', payload: { nodeIds: [mentionedEntity.id, ...competitors] } },
        ],
      };
    }
    return RESPONSE_TEMPLATES['competitors'];
  }

  // Investor queries
  if (query.includes('investor') || query.includes('invest') || query.includes('fund')) {
    return RESPONSE_TEMPLATES['investors'];
  }

  // Size/largest queries
  if (query.includes('largest') || query.includes('biggest') || query.includes('size')) {
    return RESPONSE_TEMPLATES['largest'];
  }

  // Entity specific query
  if (mentionedEntity) {
    const connections = graphData.links.filter(l => {
      const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
      const targetId = typeof l.target === 'string' ? l.target : l.target.id;
      return sourceId === mentionedEntity.id || targetId === mentionedEntity.id;
    });

    return {
      message: `${mentionedEntity.name} (${mentionedEntity.type.replace('_', ' ')}) has ${connections.length} relationships in the graph.${
        mentionedEntity.metrics?.marketCapB
          ? ` Market cap: $${mentionedEntity.metrics.marketCapB}B.`
          : ''
      }`,
      actions: [
        { type: 'zoom', label: `Focus on ${mentionedEntity.name}`, payload: { nodeId: mentionedEntity.id } },
        { type: 'highlight', label: 'Highlight Connections', payload: { nodeIds: [mentionedEntity.id] } },
      ],
    };
  }

  // Default response
  return {
    message: "I'm not sure how to help with that. Try asking about:\n• Entity relationships\n• Supply chains\n• Competitors\n• Finding paths between entities",
    actions: [],
  };
}

// Generate context-aware suggestions
function getSuggestions(selectedNode: EntityNode | null, graphData: GraphData): string[] {
  if (selectedNode) {
    return [
      `Show ${selectedNode.name}'s suppliers`,
      `Who competes with ${selectedNode.name}?`,
      `Find path from ${selectedNode.name} to...`,
    ];
  }

  const topEntities = graphData.nodes
    .filter(n => n.metrics?.marketCapB && n.metrics.marketCapB > 100)
    .slice(0, 3);

  return [
    'Show me the largest companies',
    'Find all investors',
    ...(topEntities[0] ? [`Tell me about ${topEntities[0].name}`] : []),
  ];
}

export default AIAssistant;
