<template>
    <div>
        <h1>Pharmacokinetics Database {{ version }}</h1>
        <a :href="api+'/statistics/?format=json'" title="JSON" target="_blank"><font-awesome-icon icon="code"/></a>
        <br />
        <div class="md-layout">
            <CountTable></CountTable>
        </div>
    </div>
</template>

<script>
    import CountTable from './statistics/CountTable'

    export default {
        name: 'Home',
        props: {
            api: String
        },
        components: {
            CountTable,
        }
    }
</script>

<style>
</style>