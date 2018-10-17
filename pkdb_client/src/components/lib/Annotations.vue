<template>
    <div id="annotations">
        <v-card v-if="(item.comments && item.comments.length>0) || (item.descriptions && item.descriptions.length>0)">
            <comments :comments="item.comments"/>
            <descriptions :descriptions="item.descriptions"/>
        </v-card>
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