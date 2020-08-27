<template>
  <v-navigation-drawer
      v-model="drawer"
      :mini-variant.sync="mini"
      clipped
      permanent
      right
  >
    <v-list-item class="px-2">
      <v-list-item-avatar>
        <v-icon> {{faIcon('search')}}</v-icon>
      </v-list-item-avatar>

      <v-list-item-title>Search</v-list-item-title>

      <v-btn
          icon
          @click.stop="mini = !mini"
      >
        <v-icon>{{faIcon("left_arrow")}}</v-icon>
      </v-btn>
    </v-list-item>

    <v-divider></v-divider>

    <v-list dense>
      <v-list-item
          v-for="item in items"
          :key="item.title"
          link
      >
        <v-list-item-icon>
          <v-icon>{{ item.icon }}</v-icon>
        </v-list-item-icon>

        <v-list-item-content>
          <v-list-item-title>{{ item.title }}</v-list-item-title>
        </v-list-item-content>
      </v-list-item>
    </v-list>

  </v-navigation-drawer>
</template>

<script>


export default {
  name: 'DetailDrawer',

  data: () => ({
    drawer: false,
  })
}
</script>

<style scoped>
</style>