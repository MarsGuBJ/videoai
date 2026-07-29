export type AreaNode = {
  id: string;
  name: string;
  children?: AreaNode[];
};

export const AREAS: AreaNode[] = [
  {
    id: 'area-1', name: '正门区域',
    children: [
      { id: 'area-1-1', name: '大门入口' },
      { id: 'area-1-2', name: '门卫室' },
    ],
  },
  { id: 'area-2', name: '停车场' },
  {
    id: 'area-3', name: '办公楼',
    children: [
      { id: 'area-3-1', name: '一楼大厅' },
      { id: 'area-3-2', name: '二楼走廊' },
    ],
  },
];

export const SAMPLE_AREAS: AreaNode[] = [
  { id: 'root', name: '全部设备' },
  ...AREAS,
];

export const AREA_OPTIONS: { id: string; name: string }[] = AREAS.map((a) => ({
  id: a.id,
  name: a.name,
}));

export function findAreaName(id: string): string {
  for (const root of SAMPLE_AREAS) {
    if (root.id === id) return root.name;
    if (root.children) {
      for (const child of root.children) {
        if (child.id === id) return child.name;
      }
    }
  }
  return id;
}
