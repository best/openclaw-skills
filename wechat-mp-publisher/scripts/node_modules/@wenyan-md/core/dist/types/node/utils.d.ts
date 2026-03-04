import crypto from "node:crypto";
export declare function readFileContent(filePath: string): Promise<string>;
export declare function readBinaryFile(filePath: string): Promise<Buffer>;
export declare function safeReadJson<T>(file: string, fallback: T): Promise<T>;
export declare function safeWriteJson(file: string, data: unknown): Promise<void>;
export declare function ensureDir(dir: string): Promise<void>;
export declare function md5FromBuffer(buf: crypto.BinaryLike): string;
export declare function md5FromFile(filePath: string): Promise<string>;
/**
 * 路径标准化工具函数
 * 将 Windows 的反斜杠 \ 转换为正斜杠 /，并去除末尾斜杠
 * 目的：在 Linux 容器内也能正确处理 Windows 路径字符串
 */
export declare function normalizePath(p: string): string;
export declare function isAbsolutePath(path: string): boolean;
export declare function getNormalizeFilePath(inputPath: string): string;
