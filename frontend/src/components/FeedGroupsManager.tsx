import { useState, useRef, useEffect } from 'react';
import {
  ChevronDown,
  ChevronRight,
  FolderPlus,
  Pencil,
  Trash2,
  GripVertical,
  Check,
  X,
  MoreHorizontal,
  FolderOpen,
  Folder,
  ChevronUp,
} from 'lucide-react';
import { clsx } from 'clsx';

// Types
interface Feed {
  id: string;
  name: string;
  count: number;
  icon: string;
  groupId?: string;
  sortOrder: number;
  enabled: boolean;
}

interface FeedGroup {
  id: string;
  name: string;
  color?: string;
  icon?: string;
  sortOrder: number;
  isCollapsed: boolean;
}

interface FeedGroupsManagerProps {
  groups: FeedGroup[];
  feeds: Feed[];
  selectedFeedId: string;
  onSelectFeed: (feedId: string) => void;
  onCreateGroup: (name: string) => void;
  onRenameGroup: (groupId: string, newName: string) => void;
  onDeleteGroup: (groupId: string) => void;
  onToggleGroup: (groupId: string) => void;
  onReorderGroups: (groups: FeedGroup[]) => void;
  onReorderFeeds: (feeds: Feed[]) => void;
  onMoveFeedToGroup: (feedId: string, groupId: string | null) => void;
  onCollapseAll: () => void;
  onExpandAll: () => void;
}

// Inline edit component
function InlineEdit({
  value,
  onSave,
  onCancel,
}: {
  value: string;
  onSave: (value: string) => void;
  onCancel: () => void;
}) {
  const [editValue, setEditValue] = useState(value);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (editValue.trim()) {
        onSave(editValue.trim());
      }
    } else if (e.key === 'Escape') {
      onCancel();
    }
  };

  return (
    <div className="flex items-center gap-1">
      <input
        ref={inputRef}
        type="text"
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => editValue.trim() && onSave(editValue.trim())}
        className="flex-1 px-1.5 py-0.5 text-sm bg-white dark:bg-gray-800 border border-primary-500 rounded focus:outline-none"
      />
      <button
        onClick={() => editValue.trim() && onSave(editValue.trim())}
        className="p-0.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
      >
        <Check className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={onCancel}
        className="p-0.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

// Group header component
function GroupHeader({
  group,
  feedCount,
  isEditing,
  onToggle,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onDelete,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
}: {
  group: FeedGroup;
  feedCount: number;
  isEditing: boolean;
  onToggle: () => void;
  onStartEdit: () => void;
  onSaveEdit: (name: string) => void;
  onCancelEdit: () => void;
  onDelete: () => void;
  onDragStart: (e: React.DragEvent) => void;
  onDragEnd: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
}) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div
      draggable={!isEditing}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragOver={onDragOver}
      onDrop={onDrop}
      className={clsx(
        'group flex items-center gap-1 px-2 py-1.5 text-xs font-semibold uppercase tracking-wider',
        'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded cursor-pointer'
      )}
    >
      <GripVertical className="h-3 w-3 text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 cursor-grab" />
      
      <button onClick={onToggle} className="p-0.5">
        {group.isCollapsed ? (
          <ChevronRight className="h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" />
        )}
      </button>

      {group.isCollapsed ? (
        <Folder className="h-3.5 w-3.5 text-gray-400" />
      ) : (
        <FolderOpen className="h-3.5 w-3.5 text-gray-400" />
      )}

      {isEditing ? (
        <InlineEdit value={group.name} onSave={onSaveEdit} onCancel={onCancelEdit} />
      ) : (
        <>
          <span className="flex-1 truncate" onDoubleClick={onStartEdit}>
            {group.name}
          </span>
          <span className="text-[10px] text-gray-400 tabular-nums">{feedCount}</span>
          
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowMenu(!showMenu);
              }}
              className="p-0.5 opacity-0 group-hover:opacity-100 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            >
              <MoreHorizontal className="h-3.5 w-3.5" />
            </button>
            
            {showMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowMenu(false)}
                />
                <div className="absolute right-0 top-full mt-1 z-20 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 min-w-[120px]">
                  <button
                    onClick={() => {
                      setShowMenu(false);
                      onStartEdit();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <Pencil className="h-3 w-3" />
                    Rename
                  </button>
                  <button
                    onClick={() => {
                      setShowMenu(false);
                      onDelete();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    <Trash2 className="h-3 w-3" />
                    Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// Feed item component
function FeedItem({
  feed,
  isSelected,
  onSelect,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
  indent = false,
}: {
  feed: Feed;
  isSelected: boolean;
  onSelect: () => void;
  onDragStart: (e: React.DragEvent) => void;
  onDragEnd: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  indent?: boolean;
}) {
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onClick={onSelect}
      className={clsx(
        'group flex items-center gap-2 px-2 py-1.5 text-[13px] cursor-pointer rounded',
        indent && 'ml-4',
        isSelected
          ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
          : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800/50'
      )}
    >
      <GripVertical className="h-3 w-3 text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 cursor-grab flex-shrink-0" />
      <span className="text-sm flex-shrink-0">{feed.icon}</span>
      <span className="flex-1 truncate font-medium">{feed.name}</span>
      <span className="text-[11px] text-gray-400 tabular-nums">{feed.count.toLocaleString()}</span>
    </div>
  );
}

// Main component
export function FeedGroupsManager({
  groups,
  feeds,
  selectedFeedId,
  onSelectFeed,
  onCreateGroup,
  onRenameGroup,
  onDeleteGroup,
  onToggleGroup,
  onReorderGroups,
  onReorderFeeds,
  onMoveFeedToGroup,
  onCollapseAll,
  onExpandAll,
}: FeedGroupsManagerProps) {
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null);
  const [isCreatingGroup, setIsCreatingGroup] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [draggedItem, setDraggedItem] = useState<{ type: 'group' | 'feed'; id: string } | null>(null);
  const [_dropTarget, setDropTarget] = useState<string | null>(null);
  // Note: dropTarget state is used for visual feedback during drag operations
  void _dropTarget;

  // Get feeds for a specific group
  const getFeedsForGroup = (groupId: string | null) => {
    return feeds.filter((f) => f.groupId === groupId).sort((a, b) => a.sortOrder - b.sortOrder);
  };

  // Ungrouped feeds
  const ungroupedFeeds = getFeedsForGroup(null);

  // Handle drag start
  const handleDragStart = (type: 'group' | 'feed', id: string) => (e: React.DragEvent) => {
    setDraggedItem({ type, id });
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', JSON.stringify({ type, id }));
  };

  // Handle drag end
  const handleDragEnd = () => {
    setDraggedItem(null);
    setDropTarget(null);
  };

  // Handle drag over
  const handleDragOver = (targetId: string) => (e: React.DragEvent) => {
    e.preventDefault();
    setDropTarget(targetId);
  };

  // Handle drop
  const handleDrop = (targetId: string, targetType: 'group' | 'feed') => (e: React.DragEvent) => {
    e.preventDefault();
    if (!draggedItem) return;

    if (draggedItem.type === 'group' && targetType === 'group') {
      // Reorder groups
      const draggedIndex = groups.findIndex((g) => g.id === draggedItem.id);
      const targetIndex = groups.findIndex((g) => g.id === targetId);
      if (draggedIndex !== -1 && targetIndex !== -1 && draggedIndex !== targetIndex) {
        const newGroups = [...groups];
        const [removed] = newGroups.splice(draggedIndex, 1);
        newGroups.splice(targetIndex, 0, removed);
        onReorderGroups(newGroups.map((g, i) => ({ ...g, sortOrder: i })));
      }
    } else if (draggedItem.type === 'feed') {
      if (targetType === 'group') {
        // Move feed to group
        onMoveFeedToGroup(draggedItem.id, targetId);
      } else if (targetType === 'feed') {
        // Reorder feeds
        const targetFeed = feeds.find((f) => f.id === targetId);
        if (targetFeed) {
          const groupFeeds = getFeedsForGroup(targetFeed.groupId || null);
          const draggedIndex = groupFeeds.findIndex((f) => f.id === draggedItem.id);
          const targetIndex = groupFeeds.findIndex((f) => f.id === targetId);
          
          if (draggedIndex !== -1 && targetIndex !== -1) {
            const newFeeds = [...groupFeeds];
            const [removed] = newFeeds.splice(draggedIndex, 1);
            newFeeds.splice(targetIndex, 0, removed);
            onReorderFeeds(newFeeds.map((f, i) => ({ ...f, sortOrder: i })));
          }
        }
      }
    }

    handleDragEnd();
  };

  // Create new group
  const handleCreateGroup = () => {
    if (newGroupName.trim()) {
      onCreateGroup(newGroupName.trim());
      setNewGroupName('');
      setIsCreatingGroup(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Feeds
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={onCollapseAll}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            title="Collapse all"
          >
            <ChevronUp className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onExpandAll}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            title="Expand all"
          >
            <ChevronDown className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setIsCreatingGroup(true)}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            title="New group"
          >
            <FolderPlus className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* New Group Input */}
      {isCreatingGroup && (
        <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-1">
            <FolderPlus className="h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreateGroup();
                if (e.key === 'Escape') setIsCreatingGroup(false);
              }}
              placeholder="New group name..."
              autoFocus
              className="flex-1 px-2 py-1 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:border-primary-500"
            />
            <button
              onClick={handleCreateGroup}
              disabled={!newGroupName.trim()}
              className="p-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded disabled:opacity-50"
            >
              <Check className="h-4 w-4" />
            </button>
            <button
              onClick={() => setIsCreatingGroup(false)}
              className="p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Feed List */}
      <div className="flex-1 overflow-y-auto py-2 px-1">
        {/* "All" Feed */}
        <FeedItem
          feed={{ id: 'all', name: 'All Articles', count: feeds.reduce((sum, f) => sum + f.count, 0), icon: '📰', sortOrder: -1, enabled: true }}
          isSelected={selectedFeedId === 'all'}
          onSelect={() => onSelectFeed('all')}
          onDragStart={() => {}}
          onDragEnd={() => {}}
          onDragOver={() => {}}
          onDrop={() => {}}
        />

        {/* Groups with their feeds */}
        {groups
          .sort((a, b) => a.sortOrder - b.sortOrder)
          .map((group) => {
            const groupFeeds = getFeedsForGroup(group.id);
            return (
              <div key={group.id} className="mt-2">
                <GroupHeader
                  group={group}
                  feedCount={groupFeeds.length}
                  isEditing={editingGroupId === group.id}
                  onToggle={() => onToggleGroup(group.id)}
                  onStartEdit={() => setEditingGroupId(group.id)}
                  onSaveEdit={(name) => {
                    onRenameGroup(group.id, name);
                    setEditingGroupId(null);
                  }}
                  onCancelEdit={() => setEditingGroupId(null)}
                  onDelete={() => {
                    if (confirm(`Delete group "${group.name}"? Feeds will be moved to ungrouped.`)) {
                      onDeleteGroup(group.id);
                    }
                  }}
                  onDragStart={handleDragStart('group', group.id)}
                  onDragEnd={handleDragEnd}
                  onDragOver={handleDragOver(group.id)}
                  onDrop={handleDrop(group.id, 'group')}
                />
                
                {!group.isCollapsed && groupFeeds.map((feed) => (
                  <FeedItem
                    key={feed.id}
                    feed={feed}
                    isSelected={selectedFeedId === feed.id}
                    onSelect={() => onSelectFeed(feed.id)}
                    onDragStart={handleDragStart('feed', feed.id)}
                    onDragEnd={handleDragEnd}
                    onDragOver={handleDragOver(feed.id)}
                    onDrop={handleDrop(feed.id, 'feed')}
                    indent
                  />
                ))}
              </div>
            );
          })}

        {/* Ungrouped feeds */}
        {ungroupedFeeds.length > 0 && (
          <div className="mt-4">
            <div className="px-2 py-1 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
              Ungrouped
            </div>
            {ungroupedFeeds.map((feed) => (
              <FeedItem
                key={feed.id}
                feed={feed}
                isSelected={selectedFeedId === feed.id}
                onSelect={() => onSelectFeed(feed.id)}
                onDragStart={handleDragStart('feed', feed.id)}
                onDragEnd={handleDragEnd}
                onDragOver={handleDragOver(feed.id)}
                onDrop={handleDrop(feed.id, 'feed')}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default FeedGroupsManager;
