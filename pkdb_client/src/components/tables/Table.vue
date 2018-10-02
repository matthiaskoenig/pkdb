<template>
    <md-table v-model="data.entries" v-if="data.count">

        <md-table-toolbar>
            <Heading :count="data.count" :icon="icon" :title="title"/>
            <JsonButton :resource_url="resource_url"/>
        </md-table-toolbar>

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
                type: Object,
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