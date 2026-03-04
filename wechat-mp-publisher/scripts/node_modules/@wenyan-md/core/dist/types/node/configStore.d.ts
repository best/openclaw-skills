export interface WenyanConfig {
    themes?: Record<string, ThemeConfigOptions>;
}
export interface ThemeConfigOptions {
    id: string;
    name?: string;
    description?: string;
    path: string;
}
export declare const configDir: string;
export declare const configPath: string;
declare class ConfigStore {
    private config;
    private initPromise;
    constructor();
    private load;
    private save;
    getConfig(): Promise<WenyanConfig>;
    getThemes(): Promise<ThemeConfigOptions[]>;
    getThemeById(themeId: string): Promise<string | undefined>;
    addThemeToConfig(name: string, content: string): Promise<void>;
    addThemeFile(themeId: string, themeContent: string): Promise<string>;
    deleteThemeFromConfig(themeId: string): Promise<void>;
    deleteThemeFile(filePath: string): Promise<void>;
}
export declare const configStore: ConfigStore;
export {};
