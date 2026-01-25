// Type declarations for react-force-graph-3d

declare module 'react-force-graph-3d' {
  import { Component, Ref } from 'react';
  import { Object3D, Camera, Scene, WebGLRenderer } from 'three';

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  export type NodeObject = Record<string, any> & {
    id?: string | number;
    x?: number;
    y?: number;
    z?: number;
    vx?: number;
    vy?: number;
    vz?: number;
    fx?: number | null;
    fy?: number | null;
    fz?: number | null;
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  export type LinkObject = Record<string, any> & {
    source?: string | number | NodeObject;
    target?: string | number | NodeObject;
  };

  export interface GraphData {
    nodes: NodeObject[];
    links: LinkObject[];
  }

  export interface ForceGraphMethods {
    // Camera
    cameraPosition(
      position?: { x?: number; y?: number; z?: number },
      lookAt?: { x: number; y: number; z: number },
      transitionMs?: number
    ): void;
    
    // Scene
    scene(): Scene;
    camera(): Camera;
    renderer(): WebGLRenderer;
    
    // Forces
    d3Force(forceName: string, forceInstance?: unknown): unknown;
    d3ReheatSimulation(): void;
    
    // Graph data
    graphData(): GraphData;
    graphData(data: GraphData): void;
    
    // Interaction
    centerAt(x?: number, y?: number, ms?: number): void;
    zoom(k?: number, ms?: number): void;
    zoomToFit(ms?: number, padding?: number, nodeFilterFn?: (node: NodeObject) => boolean): void;
    
    // Utilities
    getGraphBbox(nodeFilterFn?: (node: NodeObject) => boolean): {
      x: [number, number];
      y: [number, number];
      z: [number, number];
    };
    screen2GraphCoords(x: number, y: number, distance: number): { x: number; y: number; z: number };
    graph2ScreenCoords(x: number, y: number, z: number): { x: number; y: number };
    
    // Node/link access
    emitParticle(link: LinkObject): void;
    refresh(): void;
    pauseAnimation(): void;
    resumeAnimation(): void;
  }

  export interface ForceGraph3DProps {
    // Data
    graphData?: GraphData;
    nodeId?: string;
    linkSource?: string;
    linkTarget?: string;

    // Container
    width?: number;
    height?: number;
    backgroundColor?: string;
    showNavInfo?: boolean;

    // Node styling
    nodeRelSize?: number;
    nodeVal?: number | string | ((node: NodeObject) => number);
    nodeLabel?: string | ((node: NodeObject) => string);
    nodeVisibility?: boolean | string | ((node: NodeObject) => boolean);
    nodeColor?: string | ((node: NodeObject) => string);
    nodeAutoColorBy?: string | ((node: NodeObject) => string);
    nodeOpacity?: number;
    nodeResolution?: number;
    nodeThreeObject?: ((node: NodeObject) => Object3D) | Object3D;
    nodeThreeObjectExtend?: boolean | string | ((node: NodeObject) => boolean);

    // Link styling
    linkLabel?: string | ((link: LinkObject) => string);
    linkVisibility?: boolean | string | ((link: LinkObject) => boolean);
    linkColor?: string | ((link: LinkObject) => string);
    linkAutoColorBy?: string | ((link: LinkObject) => string);
    linkOpacity?: number;
    linkWidth?: number | string | ((link: LinkObject) => number);
    linkResolution?: number;
    linkCurvature?: number | string | ((link: LinkObject) => number);
    linkCurveRotation?: number | string | ((link: LinkObject) => number);
    linkMaterial?: ((link: LinkObject) => unknown) | unknown;
    linkThreeObject?: ((link: LinkObject) => Object3D) | Object3D;
    linkThreeObjectExtend?: boolean | string | ((link: LinkObject) => boolean);
    linkPositionUpdate?: ((sprite: Object3D, coords: { start: unknown; end: unknown }, link: LinkObject) => boolean);
    linkDirectionalArrowLength?: number | string | ((link: LinkObject) => number);
    linkDirectionalArrowColor?: string | ((link: LinkObject) => string);
    linkDirectionalArrowRelPos?: number | string | ((link: LinkObject) => number);
    linkDirectionalArrowResolution?: number;
    linkDirectionalParticles?: number | string | ((link: LinkObject) => number);
    linkDirectionalParticleSpeed?: number | string | ((link: LinkObject) => number);
    linkDirectionalParticleWidth?: number | string | ((link: LinkObject) => number);
    linkDirectionalParticleColor?: string | ((link: LinkObject) => string);
    linkDirectionalParticleResolution?: number;

    // Interaction
    onNodeClick?: (node: NodeObject, event: MouseEvent) => void;
    onNodeRightClick?: (node: NodeObject, event: MouseEvent) => void;
    onNodeHover?: (node: NodeObject | null, previousNode: NodeObject | null) => void;
    onNodeDrag?: (node: NodeObject, translate: { x: number; y: number }) => void;
    onNodeDragEnd?: (node: NodeObject, translate: { x: number; y: number }) => void;
    onLinkClick?: (link: LinkObject, event: MouseEvent) => void;
    onLinkRightClick?: (link: LinkObject, event: MouseEvent) => void;
    onLinkHover?: (link: LinkObject | null, previousLink: LinkObject | null) => void;
    onBackgroundClick?: (event: MouseEvent) => void;
    onBackgroundRightClick?: (event: MouseEvent) => void;
    linkHoverPrecision?: number;
    enableNodeDrag?: boolean;
    enableNavigationControls?: boolean;
    enablePointerInteraction?: boolean;

    // Force engine
    forceEngine?: 'd3' | 'ngraph';
    numDimensions?: 2 | 3;
    dagMode?: 'td' | 'bu' | 'lr' | 'rl' | 'radialout' | 'radialin' | null;
    dagLevelDistance?: number | null;
    dagNodeFilter?: (node: NodeObject) => boolean;
    onDagError?: (loopNodeIds: (string | number)[]) => void;
    d3AlphaMin?: number;
    d3AlphaDecay?: number;
    d3VelocityDecay?: number;
    ngraphPhysics?: object;
    warmupTicks?: number;
    cooldownTicks?: number;
    cooldownTime?: number;
    onEngineTick?: () => void;
    onEngineStop?: () => void;

    // Render control
    controlType?: 'trackball' | 'orbit' | 'fly';
    rendererConfig?: object;
    extraRenderers?: unknown[];
  }

  class ForceGraph3D extends Component<ForceGraph3DProps> {}

  export default ForceGraph3D;
}
