export interface MacStyle {
    getCss(): string;
}
export declare function registerMacStyle(macStyle: MacStyle): void;
export declare function getMacStyle(): MacStyle | undefined;
export declare function registerBuiltInMacStyle(): void;
export declare function getMacStyleCss(): string;
