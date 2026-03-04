import { ClientPublishOptions, StyledContent } from "./types.js";
export declare function getServerUrl(options: ClientPublishOptions): string;
export declare function getHeaders(options: ClientPublishOptions): Record<string, string>;
/**
 * 物理连通性测试
 */
export declare function healthCheck(serverUrl: string): Promise<string>;
/**
 * 鉴权探针测试
 */
export declare function verifyAuth(serverUrl: string, headers: Record<string, string>): Promise<void>;
export declare function uploadStyledContent(gzhContent: StyledContent, serverUrl: string, headers: Record<string, string>): Promise<string>;
export declare function requestServerPublish(mdFileId: string, serverUrl: string, headers: Record<string, string>, options: ClientPublishOptions): Promise<string>;
export declare function uploadLocalImages(content: string, serverUrl: string, headers: Record<string, string>, relativePath?: string): Promise<string>;
export declare function uploadCover(serverUrl: string, headers: Record<string, string>, cover?: string, relativePath?: string): Promise<string | undefined>;
