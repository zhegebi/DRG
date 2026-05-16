<template>
    <div class="drg_agent_layout">
        <DropDownMenu :title="'title'" :content="content"/>
    </div>
</template>

<script lang="ts" setup>
    import DropDownMenu from '@/components/DropDownMenu.vue';
    import {ref} from 'vue'

    const content = ref("这是")
    // setInterval(() => {
    //     content.value += "\n一个下拉菜单的内容一个下拉菜单的内容一个下拉菜单的内容一个下拉菜单的内容一个下拉菜单的内容一个下拉菜单的内容一个下拉菜单的内容一个下拉菜单的内容一个下拉菜单的内容一个下拉菜单的内容一个下拉菜单的内容一个下拉菜单的内容一个下拉菜单的内容"
    // }, 2000);
</script>

<style lang="scss" scoped>

</style>