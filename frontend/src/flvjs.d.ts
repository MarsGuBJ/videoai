declare module 'flv.js' {
  type MediaDataSource = {
    type: 'flv' | 'mp4';
    url: string;
    isLive?: boolean;
  };

  type Config = {
    enableWorker?: boolean;
    enableStashBuffer?: boolean;
    stashInitialSize?: number;
  };

  export type Player = {
    attachMediaElement(element: HTMLMediaElement): void;
    load(): void;
    play(): Promise<void>;
    destroy(): void;
    on?(event: string, handler: (...args: string[]) => void): void;
  };

  const flvjs: {
    isSupported(): boolean;
    createPlayer(source: MediaDataSource, config?: Config): Player;
  };

  export default flvjs;
}
