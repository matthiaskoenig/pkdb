<template>
    <div>
    <v-toolbar clipped-left>
        <v-toolbar-side-icon  @click.stop="drawer = !drawer" class="hidden-md-and-up"></v-toolbar-side-icon>
        <v-toolbar-title>Title</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-toolbar-items class="hidden-sm-and-down">
            <v-btn flat>Link One</v-btn>
            <v-btn flat>Link Two</v-btn>
            <v-btn flat>Link Three</v-btn>
        </v-toolbar-items>
    </v-toolbar>

    <v-navigation-drawer
            v-model="drawer"
            temporary
            absolute
            width = "200"
            id = "drawer"
    >
    </v-navigation-drawer>
    </div>
</template>

<script>
    export default {
        name: "NavigationTest",
    }
</script>

<style scoped>

</style>