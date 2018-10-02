<template>
    <md-table v-model="data.entries" v-if="data.count">

        <md-table-toolbar v-if="data.title">
            <md-badge :md-content="data.count">
                <h3 class="md-title"><font-awesome-icon icon="{{ data.icon }}" /> {{ data.title }}</h3>
            </md-badge>
        </md-table-toolbar>

        <md-table-row slot="md-table-row" slot-scope="{item}">
            <slot name="tableRow" :item="item"></slot>
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
        },
    }
</script>

<style scoped></style>