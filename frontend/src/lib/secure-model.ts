import { Capacitor, registerPlugin } from '@capacitor/core';

export interface ModelProfile {
  provider: string;
  service: 'openai' | 'openrouter' | 'gemini' | 'anthropic' | 'compatible';
  label: string;
  baseUrl: string;
  model: string;
  hasKey: boolean;
}

interface SecureModelNative {
  saveProfile(profile: Omit<ModelProfile, 'hasKey'> & { apiKey: string }): Promise<void>;
  listProfiles(): Promise<{ profiles: ModelProfile[]; activeProvider: string }>;
  setActiveProvider(options: { provider: string }): Promise<void>;
  removeProfile(options: { provider: string }): Promise<void>;
  generate(options: {
    requestId: string;
    content: string;
    conversationHistory: { role: 'user' | 'assistant'; content: string }[];
    memoryContext: string;
  }): Promise<{ content: string; tokenCount: number }>;
  cancelGeneration(): Promise<void>;
  addListener(
    eventName: 'modelDelta',
    listener: (event: { requestId: string; delta: string }) => void,
  ): Promise<{ remove: () => Promise<void> }>;
}

export const SecureModel = registerPlugin<SecureModelNative>('SecureModel');

export function secureModelAvailable(): boolean {
  return Capacitor.getPlatform() === 'android';
}
