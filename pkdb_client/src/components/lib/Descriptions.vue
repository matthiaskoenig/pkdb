<template>
    <div id="descriptions" v-if="descriptions && descriptions.length>0">
        <span class="attr">Descriptions</span><br/>
        <span v-for="item in descriptions" :key="item.pk">{{ item.text }}<br /></span>
    </div>
</template>

<script>
    export default {
        name: "Descriptions",
        props: {
            descriptions: {
                type: Array,
            }
        }
    }
</script>

<style scoped>
</style>