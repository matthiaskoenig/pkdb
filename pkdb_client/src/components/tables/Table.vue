<template>
    <md-table v-model="data.entries" v-if="data.count">

        <md-table-toolbar>
            <md-badge :md-content="data.count">
                <h3 class="md-title"><font-awesome-icon :icon="data.icon" /> {{ data.title }}</h3>
            </md-badge>
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