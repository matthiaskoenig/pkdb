<template>
    <div id="descriptions" v-if="descriptions">
        Descriptions
        <span v-for="item in descriptions" :key="item.pk">{{ item }}<br /></span>
    </div>
</template>

<script>
    export default {
        name: "Descriptions",
        props: {
            descriptions: {
                type: Object,
            }
        }
    }
</script>

<style scoped>
</style>