// Type declarations for app-level global properties registered in src/main.ts.
// The prototype registered statusClass/levelClass/priorityClass on
// app.config.globalProperties; pages call them in templates and methods.
declare module "vue" {
  interface ComponentCustomProperties {
    statusClass: (status: string) => string;
    levelClass: (level: string) => string;
    priorityClass: (priority: string) => string;
  }
}

export {};
