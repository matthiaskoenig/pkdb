<template>
    <div id="annotations">
        <comments :comments="item.comments"/>
        <descriptions :descriptions="item.descriptions"/>
    </div>
</template>

<script>
    export default {
        name: "Annotations",
        props: {
            item: {
                type: Object,
            }
        }
    }
</script>

<style scoped>
</style>