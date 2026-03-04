export declare const RuntimeEnv: {
    isContainer: boolean;
    hostFilePath: string;
    containerFilePath: string;
    resolveLocalPath(inputPath: string, relativeBase?: string): string;
};
