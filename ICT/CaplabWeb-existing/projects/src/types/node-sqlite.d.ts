// 项目保留原有 Node 类型版本，只声明本地验证库实际使用的 Node 22.13+ API。
declare module 'node:sqlite' {
  type SqlValue = string | number | null | Uint8Array;
  type Row = Record<string, SqlValue>;
  export class DatabaseSync {
    constructor(filename: string);
    exec(sql: string): void;
    prepare(sql: string): {
      run(...values: SqlValue[]): unknown;
      get(...values: SqlValue[]): Row | undefined;
      all(...values: SqlValue[]): Row[];
    };
  }
}
