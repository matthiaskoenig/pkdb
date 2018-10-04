<template>
    <md-table-toolbar>
        <Heading :count="count" :icon="icon" :title="title"/>
        <JsonButton :resource_url="resource_url"/>
    </md-table-toolbar>
</template>

<script>
    export default {
        name: "TableHeading",
        props: {
            title: {
                type: String,
            },
            count: {
                type: Number,
            },
            icon: {
                type: String,
            },
            resource_url: {
                type: String
            }
        }
    }
</script>

<style scoped>

</style>