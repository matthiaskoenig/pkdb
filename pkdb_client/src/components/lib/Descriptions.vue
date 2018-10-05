<template>
    <div id="descriptions">
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