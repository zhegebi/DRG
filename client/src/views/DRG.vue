<template>
    <div class="drg_agent_layout">
        <DropDownMenu :title="'parent'" :panel-type="'menu'" :default-open="true">
            <DropDownMenu :title="'title1'" :content="content"/>
            <DropDownMenu :title="'title2'" :content="content"/>
            <DropDownMenu :title="'title3'" :content="content"/>
            <DropDownMenu :title="'title4'" :content="content"/>
            <DropDownMenu :title="'title5'" :content="content"/>
            <DropDownMenu :title="'title6'" :content="content"/>
        </DropDownMenu>
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