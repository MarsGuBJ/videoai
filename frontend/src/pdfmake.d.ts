// pdfmake 未附带类型定义，这里以 any 声明（按需动态 import，不进主包）
declare module "pdfmake/build/pdfmake" {
  const pdfMake: any;
  export default pdfMake;
}
