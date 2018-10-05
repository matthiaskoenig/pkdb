<template>
    <div id="annotations">
        <v-card>
        <span v-if="item.comments">
            <Comments :comments="item.comments"/>
        </span>
        <span v-if="item.descriptions">
            <Descriptions :descriptions="item.descriptions"/>
        </span>

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