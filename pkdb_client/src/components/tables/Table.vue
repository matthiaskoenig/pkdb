<template>

    <md-table v-model="data.entries" v-if="data.count">
        <Heading :count="data.count" :icon="icon" :title="title" :resource_url="resource_url"/>

        <md-table-row slot="md-table-row" slot-scope="{item}">
            <slot name="row" :item="item"></slot>
        </md-table-row>
    </md-table>

</template>

<script>
    export default {
        name: "Table",
        props: {
            data: {
                type: Object,
                required: true
            },
            resource_url: {
                type: String,
            },
            title: {
                type: String,
            },
            icon: {
                type: String,
            }
        },
    }
</script>

<style scoped></style>