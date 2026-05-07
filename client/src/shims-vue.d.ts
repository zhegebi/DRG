
declare module '@jamescoyle/vue-icon' {
  import { DefineComponent } from 'vue'
  const component: DefineComponent<{ type: string; path: string }, {}, any>
  export default component
}